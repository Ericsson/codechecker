# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper commands to run CodeChecker in the tests easier.
"""
from datetime import timedelta
import json
import os
import stat
import subprocess
from subprocess import CalledProcessError
import sys
import time

import multiprocess

from codechecker_api_shared.ttypes import Permission

from codechecker_client.product import create_product_url


from . import env
from . import project


def _codechecker_cmd():
    """Return the command prefix to invoke CodeChecker.

    On Windows, scripts without .exe cannot be executed directly by
    CreateProcess. Use sys.executable to invoke the script via Python.
    """
    if sys.platform == 'win32':
        cc = env.codechecker_cmd()
        if os.path.isfile(cc):
            return [sys.executable, cc]
    return ['CodeChecker']


DEFAULT_USER_PERMISSIONS = [("cc", Permission.PRODUCT_STORE),
                            ("john", Permission.PRODUCT_STORE),
                            ("admin", Permission.PRODUCT_ADMIN)]


def call_command(cmd, cwd, environ):
    """
    Execute a process in a test case.  If the run is successful do not bloat
    the test output, but in case of any failure dump stdout and stderr.
    Returns (stdout, stderr) pair of strings.
    """
    def show(out, err):
        print("\nTEST execute stdout:\n")
        print(out)
        print("\nTEST execute stderr:\n")
        print(err)
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=environ,
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        if proc.returncode == 1:
            show(out, err)
            print('Unsuccessful run: "' + ' '.join(cmd) + '"')
        return out, err
    except OSError:
        print('Failed to run: "' + ' '.join(cmd) + '"')
        raise


def wait_for_postgres_shutdown(workspace):
    """
    Wait for PostgreSQL to shut down.
    Check if postmaster.pid file exists if yes postgres is still running.
    """
    max_wait_time = 60

    postmaster_pid_file = os.path.join(workspace,
                                       'pgsql_data',
                                       'postmaster.pid')

    while os.path.isfile(postmaster_pid_file):
        time.sleep(1)
        max_wait_time -= 1
        if max_wait_time == 0:
            break


def get_diff_results(basenames, newnames, diff_type, format_type=None,
                     extra_args=None, cc_env=None):
    """ Run diff command and get results in given format. """
    diff_cmd = [env.codechecker_cmd(), 'cmd', 'diff', diff_type]

    if format_type:
        diff_cmd.extend(['-o', format_type])

    if len(basenames) != 0:
        diff_cmd.extend(['--basename'] + basenames)
    if len(newnames) != 0:
        diff_cmd.extend(['--newname'] + newnames)

    if extra_args:
        diff_cmd.extend(extra_args)

    proc = subprocess.Popen(
        diff_cmd, encoding="utf-8", errors="ignore", env=cc_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    if proc.returncode != 1 and format_type == "json":
        return json.loads(out)['reports'], err, proc.returncode

    return out, err, proc.returncode


def create_baseline_file(report_dir: str, cc_env=None) -> str:
    """ Create baseline file from the given report directory. """
    baseline_file_path = os.path.join(report_dir, 'reports.baseline')
    parse_cmd = [
        env.codechecker_cmd(), 'parse', report_dir,
        '-e', 'baseline', '-o', baseline_file_path]

    proc = subprocess.Popen(
        parse_cmd, encoding="utf-8", errors="ignore", env=cc_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()

    return baseline_file_path


def _password_file(codechecker_cfg, test_project_path):
    """
    Return the credentials file path the CodeChecker client will read.

    The client honors CC_PASS_FILE before falling back to the home directory,
    so the test must write the throw-away credentials to the very same path
    (this is what makes login work on Windows, where HOME is not honored by
    os.path.expanduser).
    """
    return codechecker_cfg['check_env'].get(
        'CC_PASS_FILE',
        os.path.join(test_project_path, ".codechecker.passwords.json"))


def login(codechecker_cfg, test_project_path, username, password,
          protocol='http'):
    """
    Perform a command-line login to the server.
    """
    print("Logging in")
    port = str(codechecker_cfg['viewer_port'])
    login_cmd = [*_codechecker_cmd(), 'cmd', 'login', username,
                 '--url', protocol + '://' + 'localhost:' + port,
                 '--verbose', 'debug']

    auth_creds = {'client_autologin': True,
                  'credentials': {}}
    auth_file = _password_file(codechecker_cfg, test_project_path)
    if not os.path.exists(auth_file):
        # Create a default authentication file for the user, which has
        # proper structure.
        with open(auth_file, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(auth_creds, outfile)
    else:
        with open(auth_file, 'r',
                  encoding="utf-8", errors="ignore") as infile:
            auth_creds = json.load(infile)

    # Write the new credentials to the file and save it.
    auth_creds['credentials']['localhost:' + port] = username + ':' + password
    with open(auth_file, 'w',
              encoding="utf-8", errors="ignore") as outfile:
        json.dump(auth_creds, outfile)
        print("Added '" + username + ':' + password + "' to credentials file.")

    os.chmod(auth_file, stat.S_IRUSR | stat.S_IWUSR)

    try:
        print(' '.join(login_cmd))
        out = subprocess.run(
            login_cmd,
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore",
            check=False,
            capture_output=True,
            text=True,
            # Never inherit the parent's stdin: if the client ever falls back
            # to an interactive password prompt it must fail fast (EOF) instead
            # of hanging the whole test run.
            stdin=subprocess.DEVNULL
        )
        print(repr(out.stdout))
        return 0
    except OSError as cerr:
        print("Failed to call:\n" + ' '.join(login_cmd))
        print(str(cerr.errno) + ' ' + cerr.strerror)
        return cerr.errno


def logout(codechecker_cfg, test_project_path, protocol='http'):
    """
    Perform a command-line logout from a server. This method also clears the
    credentials assigned to the server.
    """
    print("Logging out")
    port = str(codechecker_cfg['viewer_port'])
    logout_cmd = [*_codechecker_cmd(), 'cmd', 'login',
                  '--logout',
                  '--url', protocol + '://'+'localhost:' + port]

    auth_file = _password_file(codechecker_cfg, test_project_path)
    if os.path.exists(auth_file):
        # Remove the credentials associated with the throw-away test server.
        with open(auth_file, 'r',
                  encoding="utf-8", errors="ignore") as infile:
            auth_creds = json.load(infile)

        try:
            del auth_creds['credentials']['localhost:' + port]

            with open(auth_file, 'w',
                      encoding="utf-8", errors="ignore") as outfile:
                json.dump(auth_creds, outfile)
                print("Removed credentials from 'localhost:" + port + "'.")
        except KeyError:
            print("Didn't remove any credentials as none were present. "
                  "Did you login()?")
    else:
        print("Credentials file did not exist. Did you login()?")

    try:
        print(' '.join(logout_cmd))
        out = subprocess.call(
            logout_cmd,
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore",
            stdin=subprocess.DEVNULL)
        print(out)
        return 0
    except OSError as cerr:
        print("Failed to call:\n" + ' '.join(logout_cmd))
        print(str(cerr.errno) + ' ' + cerr.strerror)
        return cerr.errno


def _generate_compile_commands(test_project_path):
    """Generate compile_commands.json for a test project on Windows.

    Scans for .cpp/.c files and creates entries using clang++ / clang.
    Returns the path to the generated file.
    """
    import glob
    import shutil

    sources = glob.glob(os.path.join(test_project_path, '**', '*.cpp'),
                        recursive=True)
    sources += glob.glob(os.path.join(test_project_path, '**', '*.c'),
                         recursive=True)

    compiler = shutil.which('clang++') or 'clang++'
    entries = []
    for src in sources:
        src_dir = os.path.dirname(src)
        entries.append({
            "directory": test_project_path,
            "arguments": [compiler, "-c", src, "-I", src_dir, "-o", "nul"],
            "file": src
        })

    cc_file = os.path.join(test_project_path, 'compile_commands.json')
    with open(cc_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f)
    return cc_file


def check_and_store(codechecker_cfg, test_project_name, test_project_path,
                    clean_project=True):
    """
    Check a test project and store the results into the database.

    :checkers parameter should be a list of enabled or disabled checkers
    Example: ['-d', 'deadcode.DeadStores']

    """

    output_dir = codechecker_cfg['reportdir'] \
        if 'reportdir' in codechecker_cfg \
        else os.path.join(codechecker_cfg['workspace'], 'reports')

    if clean_project:
        ret = project.clean(test_project_path)
        if ret:
            return ret

    if sys.platform == 'win32':
        # Build logging (CodeChecker log / check -b) is not supported on
        # Windows. Generate compile_commands.json and use analyze directly.
        cc_file = _generate_compile_commands(test_project_path)
        check_cmd = [*_codechecker_cmd(), 'analyze',
                     cc_file,
                     '-o', output_dir]
    else:
        build_cmd = project.get_build_cmd(test_project_path)
        check_cmd = [*_codechecker_cmd(), 'check',
                     '-o', output_dir,
                     '-b', build_cmd,
                     '--quiet']

    enabled_checkers = project.get_enabled_checkers(test_project_path)
    if enabled_checkers:
        check_cmd.append('--disable-all')
        for checker in enabled_checkers:
            check_cmd.extend(['--enable', f"checker:{checker}"])

    suppress_file = codechecker_cfg.get('suppress_file')
    if suppress_file:
        check_cmd.extend(['--suppress', suppress_file])

    skip_file = codechecker_cfg.get('skip_file')
    if skip_file:
        check_cmd.extend(['--skip', skip_file])

    clean = codechecker_cfg.get('clean')
    if clean:
        check_cmd.extend(['--clean'])

    analyzer_config = codechecker_cfg.get('analyzer_config')
    if analyzer_config:
        check_cmd.append('--analyzer-config')
        check_cmd.extend(analyzer_config)

    analyzers = codechecker_cfg.get('analyzers')
    if analyzers:
        check_cmd.append('--analyzers')
        check_cmd.extend(analyzers)

    check_cmd.extend(codechecker_cfg['checkers'])

    try:
        print("RUNNING CHECK" if sys.platform != 'win32' else
              "RUNNING ANALYZE (Windows)")
        print(check_cmd)
        process = subprocess.Popen(
            check_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()
        print(out)
        print(err)
        if sys.platform == 'win32':
            # Diagnostic: list generated report files
            import glob as _glob
            plists = _glob.glob(os.path.join(output_dir, '**', '*.plist'),
                                recursive=True)
            print(f"[DIAG] Reports dir: {output_dir}")
            print(f"[DIAG] Plist files found: {len(plists)}")
            for p in plists[:5]:
                print(f"  {p}")

    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode

    store_cmd = [*_codechecker_cmd(), 'store', '-n', test_project_name,
                 output_dir,
                 '--url', env.parts_to_url(codechecker_cfg)]

    tag = codechecker_cfg.get('tag')
    if tag:
        store_cmd.extend(['--tag', tag])

    force = codechecker_cfg.get('force')
    if force:
        store_cmd.extend(['--force'])

    description = codechecker_cfg.get('description')
    if description:
        store_cmd.extend(['--description', description])

    try:
        print('STORE' + ' '.join(store_cmd))
        proc = subprocess.Popen(
            store_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        s_out, s_err = proc.communicate()
        print(s_out)
        if s_err:
            print(s_err)
        if proc.returncode != 0:
            print(f"[DIAG] Store exited with code {proc.returncode}")
        return 0

    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


def log(codechecker_cfg, test_project_path, clean_project=False):
    """Log a test project."""
    build_cmd = project.get_build_cmd(test_project_path)
    build_json = os.path.join(codechecker_cfg['workspace'], "build.json")

    if clean_project:
        ret = project.clean(test_project_path)
        if ret:
            return ret

    log_cmd = [*_codechecker_cmd(), 'log',
               '-o', build_json,
               '-b', build_cmd,
               ]

    try:
        proc = subprocess.Popen(
            log_cmd,
            cwd=test_project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)

        return 0
    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


def analyze(codechecker_cfg, test_project_path):
    """Analyze a test project.

    A build.json file should be in the workspace directory!
    """
    build_json = os.path.join(codechecker_cfg['workspace'], "build.json")

    analyze_cmd = [*_codechecker_cmd(), 'analyze',
                   build_json,
                   '-o', codechecker_cfg['reportdir'],
                   '--analyzers', 'clangsa'
                   ]

    suppress_file = codechecker_cfg.get('suppress_file')
    if suppress_file:
        analyze_cmd.extend(['--suppress', suppress_file])

    skip_file = codechecker_cfg.get('skip_file')
    if skip_file:
        analyze_cmd.extend(['--skip', skip_file])

    analyze_cmd.extend(codechecker_cfg['checkers'])
    try:
        print('ANALYZE: ' + ' '.join(analyze_cmd))
        proc = subprocess.Popen(
            analyze_cmd,
            cwd=test_project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)
        return 0
    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


def log_and_analyze(codechecker_cfg, test_project_path, clean_project=True):
    """
    Analyze a test project.

    :checkers parameter should be a list of enabled or disabled checkers
    Example: ['-d', 'deadcode.DeadStores']

    """

    build_cmd = project.get_build_cmd(test_project_path)
    build_json = os.path.join(codechecker_cfg['workspace'], "build.json")

    if clean_project:
        ret = project.clean(test_project_path)
        if ret:
            return ret

    log_cmd = [*_codechecker_cmd(), 'log',
               '-o', build_json,
               '-b', build_cmd,
               ]

    analyzers = codechecker_cfg.get('analyzers', ['clangsa'])
    analyze_cmd = [*_codechecker_cmd(), 'analyze',
                   build_json,
                   '-o', codechecker_cfg['reportdir'],
                   '--analyzers', *analyzers
                   ]

    suppress_file = codechecker_cfg.get('suppress_file')
    if suppress_file:
        analyze_cmd.extend(['--suppress', suppress_file])

    skip_file = codechecker_cfg.get('skip_file')
    if skip_file:
        analyze_cmd.extend(['--skip', skip_file])

    analyze_cmd.extend(codechecker_cfg['checkers'])
    try:
        print("LOG: " + ' '.join(log_cmd))
        proc = subprocess.Popen(
            log_cmd,
            cwd=test_project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)

        print("ANALYZE:")
        print(analyze_cmd)
        proc = subprocess.Popen(
            analyze_cmd,
            cwd=test_project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)
        return 0
    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


def parse(codechecker_cfg):
    """
    Parse the results of the analysis and return the output.
    """

    parse_cmd = [*_codechecker_cmd(), 'parse', codechecker_cfg['reportdir']]

    try:
        print("PARSE: " + ' '.join(parse_cmd))
        proc = subprocess.Popen(
            parse_cmd,
            cwd=codechecker_cfg['workspace'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)

        return proc.returncode, out, err
    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return 1, '', ''


def store(codechecker_cfg, test_project_name):
    """
    Store results from a report dir.
    """
    report_dirs = codechecker_cfg['reportdir'] \
        if 'reportdir' in codechecker_cfg \
        else os.path.join(codechecker_cfg['workspace'], 'reports')
    if not isinstance(report_dirs, list):
        report_dirs = [report_dirs]

    store_cmd = [*_codechecker_cmd(), 'store',
                 '--url', env.parts_to_url(codechecker_cfg),
                 '--name', test_project_name,
                 *report_dirs]

    tag = codechecker_cfg.get('tag')
    if tag:
        store_cmd.extend(['--tag', tag])

    force = codechecker_cfg.get('force')
    if force:
        store_cmd.extend(['--force'])

    trim_path = codechecker_cfg.get('trim_path_prefix')
    if trim_path:
        store_cmd.extend(['--trim-path-prefix', trim_path])

    try:
        print('STORE: ' + ' '.join(store_cmd))
        proc = subprocess.Popen(
            store_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)

        return proc.returncode
    except OSError as oserr:
        print("Failed to call:\n" + ' '.join(store_cmd) +
              "\n" + oserr.strerror)
        return oserr.errno


def serv_cmd(workspace_dir, port, pg_config=None, serv_args=None):

    server_cmd = [*_codechecker_cmd(), 'server',
                  '--workspace', workspace_dir]

    server_cmd.extend(['--host', 'localhost',
                       '--port', str(port)])

    # Allow CI to override worker counts via env vars.
    api_procs = os.environ.get('CC_TEST_API_WORKERS')
    task_procs = os.environ.get('CC_TEST_TASK_WORKERS')
    if api_procs:
        server_cmd.extend(['--api-handler-processes', api_procs])
    if task_procs:
        server_cmd.extend(['--task-worker-processes', task_procs])

    server_cmd.extend(serv_args or [])

    # server_cmd.extend(['--verbose', 'debug'])

    if pg_config:
        server_cmd.append('--postgresql')
        server_cmd += _pg_db_config_to_cmdline_params(pg_config)
    else:
        server_cmd += ['--sqlite', os.path.join(workspace_dir,
                                                'config.sqlite')]

    print(' '.join(server_cmd))

    return server_cmd


def start_or_get_server(auth_required=False):
    """
    Create a global CodeChecker server with the given configuration.
    """
    workspace_root = env.get_workspace(None)

    server_type = 'global_auth_server' if auth_required else \
        'global_simple_server'

    workspace_dir = os.path.join(workspace_root, server_type)
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir)

    portfile = os.path.join(workspace_dir, 'serverport')

    if os.path.exists(portfile):
        print("A server appears to be already running...")
        with open(portfile, 'r', encoding="utf-8", errors="ignore") as f:
            port = int(f.read())
    else:
        if auth_required:
            # Set up the root user and the authentication for the server.
            env.enable_auth(workspace_dir)

        port = env.get_free_port()
        print("Setting up CodeChecker server in " + workspace_dir + " :" +
              str(port))

        with open(portfile, 'w', encoding="utf-8", errors="ignore") as f:
            f.write(str(port))

        pg_config = env.get_postgresql_cfg()

        server_cmd = serv_cmd(workspace_dir, port, pg_config)

        print("Starting server...")
        server_stdout = os.path.join(workspace_dir,
                                     str(os.getpid()) + ".out")

        with open(server_stdout, "w",
                  encoding="utf-8", errors="ignore") as server_out:
            subprocess.Popen(
                server_cmd,
                stdout=server_out,
                stderr=server_out,
                env=env.test_env(workspace_dir),
                encoding="utf-8",
                errors="ignore")

            wait_for_server_start(server_stdout, port=port)

        if pg_config:
            # The behaviour is that CodeChecker servers only configure a
            # 'Default' product in SQLite mode, if the server was started
            # brand new. But certain test modules might make use of a
            # default product, so we now manually have to create it.
            default_path = os.path.join(workspace_root, 'Default')
            if not os.path.exists(default_path):
                print("PostgreSQL server does not create 'Default' product...")
                print("Creating it now!")

                os.makedirs(default_path)
                add_test_package_product({'viewer_host': 'localhost',
                                          'viewer_port': port,
                                          'viewer_product': 'Default'},
                                         default_path)
    return {
        'viewer_host': 'localhost',
        'viewer_port': port
    }


def wait_for_server_start(stdoutfile, port=None):
    print("Waiting for server start reading file " + stdoutfile)
    n = 0
    server_start_timeout = timedelta(minutes=5)
    while True:
        if os.path.isfile(stdoutfile):
            with open(stdoutfile, encoding="utf-8", errors="ignore") as f:
                out = f.read()
                if "Server waiting for client requests" in out:
                    return

                # Handle error case when the server failed to start and gave
                # some error message.
                if "usage: CodeChecker" in out:
                    return

                # Fail fast if server crashed during startup.
                if "Config database initialization failed" in out \
                        or "Failed to create schema" in out:
                    print(f"[DIAG] Server FATAL error after "
                          f"{n}s. Output:")
                    print(out[-2000:])

        # Fallback: check if server can handle HTTP requests.
        if port and n > 3:
            import urllib.request
            try:
                urllib.request.urlopen(
                    f"http://localhost:{port}/", timeout=1)
            except urllib.error.HTTPError:
                # Any HTTP response (even 404) means server is ready.
                print(f"Server responding on port {port} after {n}s")
                return
            except (ConnectionRefusedError, OSError, urllib.error.URLError):
                pass

        if n > server_start_timeout.total_seconds():
            print("[FATAL!] Server failed to start after "
                  f"'{str(server_start_timeout)}' "
                  f"({server_start_timeout.total_seconds()} seconds). "
                  "There is likely a major issue preventing startup!")
            if os.path.isfile(stdoutfile):
                with open(stdoutfile, encoding='utf-8') as f:
                    print("*** HERE FOLLOWS THE OUTPUT OF THE 'server' "
                          "COMMAND! ***")
                    print(f.read())
                    print("*** END 'server' OUTPUT ***")

            raise TimeoutError("Server failed to start in a timely manner")

        time.sleep(1)
        n += 1
        print("Waiting for server to start for " + str(n) + " seconds...")


# This server uses multiple custom servers, which are brought up here
# and torn down by the package itself --- it does not connect to the
# test run's "master" server.
def start_server(codechecker_cfg, event, server_args=None, pg_config=None):
    """Start the CodeChecker server."""
    def start_server_proc(event, server_cmd, checking_env):
        """Target function for starting the CodeChecker server."""
        # Redirecting stdout to a file
        server_stdout = os.path.join(codechecker_cfg['workspace'],
                                     str(os.getpid()) + ".out")
        print("Redirecting server output to " + server_stdout)
        with open(server_stdout, "w",
                  encoding="utf-8", errors="ignore") as server_out:
            proc = subprocess.Popen(
                server_cmd,
                env=checking_env,
                stdout=server_out,
                stderr=server_out,
                encoding="utf-8",
                errors="ignore")

            # Blocking termination until event is set.
            event.wait()

            # If proc is still running, stop it.
            if proc.poll() is None:
                proc.terminate()

    server_cmd = serv_cmd(codechecker_cfg['workspace'],
                          str(codechecker_cfg['viewer_port']),
                          pg_config,
                          server_args or [])

    server_proc = multiprocess.Process(
        name='server',
        target=start_server_proc,
        args=(event, server_cmd, codechecker_cfg['check_env']))

    server_proc.start()
    server_output_file = os.path.join(codechecker_cfg['workspace'],
                                      str(server_proc.pid) + ".out")
    wait_for_server_start(server_output_file,
                          port=codechecker_cfg['viewer_port'])

    return {
        'viewer_host': 'localhost',
        'viewer_port': codechecker_cfg['viewer_port'],
        'server_output_file': server_output_file
    }


def add_test_package_product(server_data, test_folder, check_env=None,
                             protocol='http', report_limit=None,
                             user_permissions=None,
                             database_name="default"):
    """
    Add a product for a test suite to the server provided by server_data.
    Server must be running before called.

    server_data must contain three keys: viewer_{host, port, product}.
    """

    if user_permissions is None:
        user_permissions = DEFAULT_USER_PERMISSIONS

    if not check_env:
        check_env = env.test_env(test_folder)

    codechecker_cfg = {'check_env': check_env}
    codechecker_cfg.update(server_data)

    # Clean the previous session if any exists.
    logout(codechecker_cfg, test_folder, protocol)

    url = create_product_url(protocol, server_data['viewer_host'],
                             str(server_data['viewer_port']),
                             '')

    add_command = [*_codechecker_cmd(), 'cmd', 'products', 'add',
                   server_data['viewer_product'],
                   '--url', url,
                   '--name', os.path.basename(test_folder),
                   '--description', "Automatically created product for test.",
                   '--verbose', 'debug']
    if report_limit:
        add_command.extend(['--report-limit', str(report_limit)])

    # If tests are running on postgres, we need to create a database.
    pg_config = env.get_postgresql_cfg()
    if pg_config:
        env.add_database(server_data['viewer_product'], check_env)

        add_command.append('--postgresql')
        pg_config['dbname'] = server_data['viewer_product']

        if os.environ.get('PGPASSWORD'):
            pg_config['dbpassword'] = os.environ['PGPASSWORD']

        add_command += _pg_db_config_to_cmdline_params(pg_config)
    else:
        # SQLite databases are put under the workspace of the appropriate test.
        if database_name == 'default':
            database_name = os.path.basename(test_folder)
        database_name += '.sqlite'
        add_command += ['--sqlite', database_name]

    print(' '.join(add_command))

    # Authenticate as SUPERUSER to be able to create the product.
    login(codechecker_cfg, test_folder, "root", "root", protocol)
    # The schema creation is a synchronous call.
    returncode = subprocess.call(
        add_command,
        env=check_env,
        encoding="utf-8",
        errors="ignore",
        stdin=subprocess.DEVNULL)

    pr_client = env.setup_product_client(test_folder,
                                         product=server_data['viewer_product'],
                                         host=server_data['viewer_host'],
                                         port=server_data['viewer_port'])
    product_id = pr_client.getCurrentProduct().id

    # Setup an authentication client for creating sessions.
    auth_client = env.setup_auth_client(test_folder,
                                        host=server_data['viewer_host'],
                                        port=server_data['viewer_port'])

    extra_params = '{"productID":' + str(product_id) + '}'

    # Give permissions for the users.
    for user, permission in user_permissions:
        ret = auth_client.addPermission(permission,
                                        user,
                                        False,
                                        extra_params)
        if not ret:
            raise RuntimeError("Failed to add permission to " + user)

    logout(codechecker_cfg, test_folder, protocol)

    # After login as SUPERUSER, continue running the test as a normal user.
    # login() saves the relevant administrative file
    login(codechecker_cfg, test_folder, "cc", "test", protocol)

    if returncode:
        raise RuntimeError("Failed to add the product to the test server!")


def remove_test_package_product(test_folder, check_env=None, protocol='http',
                                product=None):
    """
    Remove the product associated with the given test folder.
    The folder must exist, as the server configuration is read from the folder.
    """

    if not check_env:
        check_env = env.test_env(test_folder)

    server_data = env.import_test_cfg(test_folder)['codechecker_cfg']
    print(server_data)
    product_to_remove = product if product else server_data['viewer_product']

    if 'check_env' not in server_data:
        server_data['check_env'] = check_env

    # Clean the previous session if any exists.
    logout(server_data, test_folder, protocol)
    url = create_product_url(protocol, server_data['viewer_host'],
                             str(server_data['viewer_port']),
                             '')
    del_command = [*_codechecker_cmd(), 'cmd', 'products', 'del',
                   product_to_remove, '--url', url]

    print(' '.join(del_command))

    # Authenticate as SUPERUSER to be able to delete the product.
    login(server_data, test_folder, "root", "root", protocol)
    returncode = subprocess.call(
        del_command,
        env=check_env,
        encoding="utf-8",
        errors="ignore",
        stdin=subprocess.DEVNULL)
    logout(server_data, test_folder, protocol)

    # If tests are running on postgres, we need to delete the database.
    # SQLite databases are deleted automatically as part of the
    # workspace removal.
    if env.get_postgresql_cfg():
        env.del_database(product_to_remove, check_env)

    if returncode:
        raise RuntimeError(
            "Failed to remove the product from the test server!")


def _pg_db_config_to_cmdline_params(pg_db_config):
    """Format postgres config dict to CodeChecker cmdline parameters."""
    params = []

    for key, value in pg_db_config.items():
        params.append('--' + key)
        params.append(str(value))

    return params
