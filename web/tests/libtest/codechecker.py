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


import json
import multiprocessing
import os
import shlex
import stat
import subprocess
from subprocess import CalledProcessError
import time

from codechecker_api_shared.ttypes import Permission

from codechecker_client.product import create_product_url

from . import env
from . import project


DEFAULT_USER_PERMISSIONS = [("cc", Permission.PRODUCT_STORE),
                            ("john", Permission.PRODUCT_STORE),
                            ("admin", Permission.PRODUCT_ADMIN)]


def call_command(cmd, cwd, env):
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()
        if proc.returncode == 1:
            show(out, err)
            print('Unsuccessful run: "' + ' '.join(cmd) + '"')
            raise Exception("Unsuccessful run of command.")
        return out, err
    except OSError:
        show(out, err)
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

    diff_cmd.extend(['--basename'] + basenames)
    diff_cmd.extend(['--newname'] + newnames)

    if extra_args:
        diff_cmd.extend(extra_args)

    proc = subprocess.Popen(
        diff_cmd, encoding="utf-8", errors="ignore", env=cc_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    if format_type == "json":
        return json.loads(out), err, proc.returncode

    return out, err, proc.returncode


def login(codechecker_cfg, test_project_path, username, password,
          protocol='http'):
    """
    Perform a command-line login to the server.
    """
    print("Logging in")
    port = str(codechecker_cfg['viewer_port'])
    login_cmd = ['CodeChecker', 'cmd', 'login', username,
                 '--url', protocol + '://' + 'localhost:' + port,
                 '--verbose', 'debug']

    auth_creds = {'client_autologin': True,
                  'credentials': {}}
    auth_file = os.path.join(test_project_path, ".codechecker.passwords.json")
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
        out = subprocess.call(
            shlex.split(
                ' '.join(login_cmd)),
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        print(out)
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
    logout_cmd = ['CodeChecker', 'cmd', 'login',
                  '--logout',
                  '--url', protocol + '://'+'localhost:' + port]

    auth_file = os.path.join(test_project_path, ".codechecker.passwords.json")
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
            shlex.split(
                ' '.join(logout_cmd)),
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
        print(out)
        return 0
    except OSError as cerr:
        print("Failed to call:\n" + ' '.join(logout_cmd))
        print(str(cerr.errno) + ' ' + cerr.strerror)
        return cerr.errno


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

    build_cmd = project.get_build_cmd(test_project_path)

    if clean_project:
        ret = project.clean(test_project_path)
        if ret:
            return ret

    check_cmd = ['CodeChecker', 'check',
                 '-o', output_dir,
                 '-b', build_cmd,
                 '--quiet']

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

    check_cmd.extend(codechecker_cfg['checkers'])

    try:
        print("RUNNING CHECK")
        print(check_cmd)
        subprocess.call(
            check_cmd,
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")

    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode

    store_cmd = ['CodeChecker', 'store', '-n', test_project_name,
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
        store_cmd.extend(['--description', "'" + description + "'"])

    try:
        print('STORE' + ' '.join(store_cmd))
        subprocess.call(
            shlex.split(
                ' '.join(store_cmd)),
            cwd=test_project_path,
            env=codechecker_cfg['check_env'],
            encoding="utf-8",
            errors="ignore")
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

    log_cmd = ['CodeChecker', 'log',
               '-o', build_json,
               '-b', "'" + build_cmd + "'",
               ]

    try:
        proc = subprocess.Popen(
            shlex.split(
                ' '.join(log_cmd)),
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

    analyze_cmd = ['CodeChecker', 'analyze',
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
            shlex.split(
                ' '.join(analyze_cmd)),
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

    log_cmd = ['CodeChecker', 'log',
               '-o', build_json,
               '-b', "'" + build_cmd + "'",
               ]

    analyzers = codechecker_cfg.get('analyzers', ['clangsa'])
    analyze_cmd = ['CodeChecker', 'analyze',
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
            shlex.split(
                ' '.join(log_cmd)),
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
        print(shlex.split(' '.join(analyze_cmd)))
        proc = subprocess.Popen(
            shlex.split(
                ' '.join(analyze_cmd)),
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

    parse_cmd = ['CodeChecker', 'parse', codechecker_cfg['reportdir']]

    try:
        print("PARSE: " + ' '.join(parse_cmd))
        proc = subprocess.Popen(
            shlex.split(
                ' '.join(parse_cmd)),
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
    report_dirs = codechecker_cfg['reportdir']
    if not isinstance(report_dirs, list):
        report_dirs = [report_dirs]

    store_cmd = ['CodeChecker', 'store',
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
            shlex.split(
                ' '.join(store_cmd)),
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


def serv_cmd(config_dir, port, pg_config=None, serv_args=None):

    server_cmd = ['CodeChecker', 'server',
                  '--config-directory', config_dir]

    server_cmd.extend(['--host', 'localhost',
                       '--port', str(port)])

    server_cmd.extend(serv_args or [])

    # server_cmd.extend(['--verbose', 'debug'])

    if pg_config:
        server_cmd.append('--postgresql')
        server_cmd += _pg_db_config_to_cmdline_params(pg_config)
    else:
        server_cmd += ['--sqlite', os.path.join(config_dir, 'config.sqlite')]

    print(' '.join(server_cmd))

    return server_cmd


def start_or_get_server(auth_required=False):
    """
    Create a global CodeChecker server with the given configuration.
    """
    workspace_root = env.get_workspace(None)

    server_type = 'global_auth_server' if auth_required else \
        'global_simple_server'

    config_dir = os.path.join(workspace_root, server_type)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    portfile = os.path.join(config_dir, 'serverport')

    if os.path.exists(portfile):
        print("A server appears to be already running...")
        with open(portfile, 'r', encoding="utf-8", errors="ignore") as f:
            port = int(f.read())
    else:
        if auth_required:
            # Set up the root user and the authentication for the server.
            env.enable_auth(config_dir)

        port = env.get_free_port()
        print("Setting up CodeChecker server in " + config_dir + " :" +
              str(port))

        with open(portfile, 'w', encoding="utf-8", errors="ignore") as f:
            f.write(str(port))

        pg_config = env.get_postgresql_cfg()

        server_cmd = serv_cmd(config_dir, port, pg_config)

        print("Starting server...")
        server_stdout = os.path.join(config_dir,
                                     str(os.getpid()) + ".out")

        with open(server_stdout, "w",
                  encoding="utf-8", errors="ignore") as server_out:
            subprocess.Popen(
                server_cmd,
                stdout=server_out,
                stderr=server_out,
                env=env.test_env(config_dir),
                encoding="utf-8",
                errors="ignore")

            wait_for_server_start(server_stdout)

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


def wait_for_server_start(stdoutfile):
    print("Waiting for server start reading file " + stdoutfile)
    n = 0
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

    server_proc = multiprocessing.Process(
        name='server',
        target=start_server_proc,
        args=(event, server_cmd, codechecker_cfg['check_env']))

    server_proc.start()
    server_output_file = os.path.join(codechecker_cfg['workspace'],
                                      str(server_proc.pid) + ".out")
    wait_for_server_start(server_output_file)

    return {
        'viewer_host': 'localhost',
        'viewer_port': codechecker_cfg['viewer_port'],
        'server_output_file': server_output_file
    }


def add_test_package_product(server_data, test_folder, check_env=None,
                             protocol='http',
                             user_permissions=DEFAULT_USER_PERMISSIONS):
    """
    Add a product for a test suite to the server provided by server_data.
    Server must be running before called.

    server_data must contain three keys: viewer_{host, port, product}.
    """

    if not check_env:
        check_env = env.test_env(test_folder)

    codechecker_cfg = {'check_env': check_env}
    codechecker_cfg.update(server_data)

    # Clean the previous session if any exists.
    logout(codechecker_cfg, test_folder, protocol)

    url = create_product_url(protocol, server_data['viewer_host'],
                             str(server_data['viewer_port']),
                             '')

    add_command = ['CodeChecker', 'cmd', 'products', 'add',
                   server_data['viewer_product'],
                   '--url', url,
                   '--name', os.path.basename(test_folder),
                   '--description', "Automatically created product for test.",
                   '--verbose', 'debug']

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
        add_command += ['--sqlite',
                        os.path.join(test_folder, 'data.sqlite')]

    print(' '.join(add_command))

    # Authenticate as SUPERUSER to be able to create the product.
    login(codechecker_cfg, test_folder, "root", "root", protocol)
    # The schema creation is a synchronous call.
    returncode = subprocess.call(
        add_command,
        env=check_env,
        encoding="utf-8",
        errors="ignore")

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
            raise Exception("Failed to add permission to " + user)

    logout(codechecker_cfg, test_folder, protocol)

    # After login as SUPERUSER, continue running the test as a normal user.
    # login() saves the relevant administrative file
    login(codechecker_cfg, test_folder, "cc", "test", protocol)

    if returncode:
        raise Exception("Failed to add the product to the test server!")


def remove_test_package_product(test_folder, check_env=None, protocol='http'):
    """
    Remove the product associated with the given test folder.
    The folder must exist, as the server configuration is read from the folder.
    """

    if not check_env:
        check_env = env.test_env(test_folder)

    server_data = env.import_test_cfg(test_folder)['codechecker_cfg']
    print(server_data)

    if 'check_env' not in server_data:
        server_data['check_env'] = check_env

    # Clean the previous session if any exists.
    logout(server_data, test_folder, protocol)
    url = create_product_url(protocol, server_data['viewer_host'],
                             str(server_data['viewer_port']),
                             '')
    del_command = ['CodeChecker', 'cmd', 'products', 'del',
                   server_data['viewer_product'],
                   '--url', url]

    print(' '.join(del_command))

    # Authenticate as SUPERUSER to be able to create the product.
    login(server_data, test_folder, "root", "root", protocol)
    returncode = subprocess.call(
        del_command,
        env=check_env,
        encoding="utf-8",
        errors="ignore")
    logout(server_data, test_folder, protocol)

    # If tests are running on postgres, we need to delete the database.
    # SQLite databases are deleted automatically as part of the
    # workspace removal.
    if env.get_postgresql_cfg():
        env.del_database(server_data['viewer_product'], check_env)

    if returncode:
        raise Exception("Failed to remove the product from the test server!")


def _pg_db_config_to_cmdline_params(pg_db_config):
    """Format postgres config dict to CodeChecker cmdline parameters."""
    params = []

    for key, value in pg_db_config.items():
        params.append('--' + key)
        params.append(str(value))

    return params
