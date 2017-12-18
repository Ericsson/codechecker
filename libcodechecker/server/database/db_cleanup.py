from codeCheckerDBAccess_v6.ttypes import*

from libcodechecker.logger import LoggerFactory
from libcodechecker.server.database.run_db_model import *

LOG = LoggerFactory.get_new_logger('DB CLEANUP')


def remove_unused_files(session):
    LOG.info("Garbage collection of dangling files started...")

    bpe_files = session.query(BugPathEvent.file_id) \
        .group_by(BugPathEvent.file_id) \
        .subquery()
    brp_files = session.query(BugReportPoint.file_id) \
        .group_by(BugReportPoint.file_id) \
        .subquery()

    session.query(File) \
        .filter(File.id.notin_(bpe_files),
                File.id.notin_(brp_files)) \
        .delete(synchronize_session=False)

    files = session.query(File.content_hash) \
        .group_by(File.content_hash) \
        .subquery()

    session.query(FileContent) \
        .filter(FileContent.content_hash.notin_(files)) \
        .delete(synchronize_session=False)

    LOG.info("Garbage collection of dangling files finished.")
