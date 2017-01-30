import os
import shlex
import socket
import subprocess
import time

from subprocess import CalledProcessError

from . import project


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


def check(codechecker_cfg, test_project_name, test_project_path):
    """
    Check a test project.

    :checkers parameter should be a list of enabled or disabled checkers
    Example: ['-d', 'deadcode.DeadStores']

    """

    build_cmd = project.get_build_cmd(test_project_path)

    check_cmd = ['CodeChecker', 'check',
                 '-w', codechecker_cfg['workspace'],
                 '-n', test_project_name,
                 '-b', "'" + build_cmd + "'",
                 '--analyzers', 'clangsa',
                 '--quiet-build']

    suppress_file = codechecker_cfg.get('suppress_file')
    if suppress_file:
        check_cmd.extend(['--suppress', suppress_file])

    skip_file = codechecker_cfg.get('skip_file')
    if skip_file:
        check_cmd.extend(['--skip', skip_file])

    check_cmd.extend(codechecker_cfg['checkers'])

    psql_cfg = codechecker_cfg.get('pg_db_config')
    if psql_cfg:
        check_cmd.append('--postgresql')
        check_cmd += _pg_db_config_to_cmdline_params(psql_cfg)

    try:
        print(' '.join(check_cmd))
        proc = subprocess.Popen(shlex.split(' '.join(check_cmd)),
                                cwd=test_project_path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=codechecker_cfg['check_env'])
        out, err = proc.communicate()
        print(out)
        print(err)
        return 0

    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


def serv_cmd(codechecker_cfg, test_config):

    server_cmd = ['CodeChecker', 'server',
                  '-w', codechecker_cfg['workspace']]

    suppress_file = codechecker_cfg.get('suppress_file')
    if suppress_file:
        server_cmd.extend(['--suppress', suppress_file])

    server_cmd.extend(['--check-port',
                       str(codechecker_cfg['server_port']),
                       '--view-port',
                       str(codechecker_cfg['viewer_port'])
                       ])

    psql_cfg = codechecker_cfg.get('pg_db_config')
    if psql_cfg:
        server_cmd.append('--postgresql')
        server_cmd += _pg_db_config_to_cmdline_params(psql_cfg)

    print(server_cmd)

    return server_cmd


def _pg_db_config_to_cmdline_params(pg_db_config):
    """Format postgres config dict to CodeChecker cmdline parameters."""
    params = []

    for key, value in pg_db_config.items():
        params.append('--' + key)
        params.append(str(value))

    return params
