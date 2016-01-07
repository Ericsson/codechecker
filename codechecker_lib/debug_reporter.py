# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import sys

import sqlalchemy

from db_model.orm_model import *

from codechecker_lib import analyzer_env
from codechecker_lib import logger
from codechecker_lib import analyzer_crash_handler
from codechecker_lib import util
from codechecker_lib import database_handler

LOG = logger.get_new_logger('DEBUG_REPORTER')


# -----------------------------------------------------------------------------
def get_dump_file_name(run_id, action_id):
    return 'action_' + str(run_id) + '_' + str(action_id) + '_dump.log'


# -----------------------------------------------------------------------------
def debug(context, connection_string, force):
    try:
        engine = database_handler.SQLServer.create_engine(connection_string)
        session = sqlalchemy.orm.scoped_session(
                    sqlalchemy.orm.sessionmaker(bind=engine))

        # Get latest run id
        last_run = session.query(Run).order_by(Run.id.desc()).first()

        # Get all failed actions
        actions = session.query(BuildAction).filter(and_(
                    BuildAction.run_id == last_run.id,
                    sqlalchemy.sql.func.length(BuildAction.failure_txt) != 0))

        debug_env = analyzer_env.get_check_env(context.path_env_extra,
                                                 context.ld_lib_path_extra)

        crash_handler = analyzer_crash_handler.AnalyzerCrashHandler(context,
                                                                    debug_env)

        dumps_dir = context.dump_output_dir
        if not os.path.exists(dumps_dir):
            os.mkdir(dumps_dir)

        for action in actions:
            LOG.info('Processing action ' + str(action.id) + '.')
            debug_log_file = \
                os.path.join(dumps_dir, get_dump_file_name(last_run.id, action.id))
            if not force and os.path.exists(debug_log_file):
                LOG.info('This file already exists.')
                continue

            LOG.info('Generating stacktrace with gdb.')

            gdb_result = \
                crash_handler.get_crash_info(str(action.check_cmd).split())

            LOG.info('Writing debug info to file.')

            with open(debug_log_file, 'w') as log_file:
                log_file.write('========================\n')
                log_file.write('Original build command: \n')
                log_file.write('========================\n')
                log_file.write(action.build_cmd + '\n')
                log_file.write('===============\n')
                log_file.write('Check command: \n')
                log_file.write('===============\n')
                log_file.write(action.check_cmd + '\n')
                log_file.write('==============\n')
                log_file.write('Failure text: \n')
                log_file.write('==============\n')
                log_file.write(action.failure_txt + '\n')
                log_file.write('==========\n')
                log_file.write('GDB info: \n')
                log_file.write('==========\n')
                log_file.write(gdb_result)

        LOG.info('All new debug files are placed in ' + dumps_dir)

    except KeyboardInterrupt as kb_exc:
        LOG.error(str(kb_exc))
        sys.exit(1)
