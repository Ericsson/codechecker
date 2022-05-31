# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
SQLAlchemy ORM model for the analysis run storage database.
"""
from datetime import datetime, timedelta
from math import ceil
import os

from sqlalchemy import MetaData, Column, Integer, UniqueConstraint, String, \
    DateTime, Boolean, ForeignKey, Binary, Enum, Table, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import true, false

CC_META = MetaData(naming_convention={
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

# Create base class for ORM classes.
Base = declarative_base(metadata=CC_META)


class AnalysisInfo(Base):
    __tablename__ = 'analysis_info'

    id = Column(Integer, autoincrement=True, primary_key=True)
    analyzer_command = Column(Binary)

    def __init__(self, analyzer_command):
        self.analyzer_command = analyzer_command


class Run(Base):
    __tablename__ = 'runs'

    __table_args__ = (
        UniqueConstraint('name'),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    date = Column(DateTime)
    duration = Column(Integer)  # Seconds, -1 if unfinished.
    name = Column(String)
    version = Column(String)
    can_delete = Column(Boolean, nullable=False, server_default=true(),
                        default=True)

    def __init__(self, name, version):
        self.date, self.name, self.version = datetime.now(), name, version
        self.duration = -1

    def mark_finished(self):
        if self.duration == -1:
            self.duration = ceil((datetime.now() - self.date).total_seconds())


class RunLock(Base):
    """
    Represents a lock record for a particular run name, constituting that the
    run identified by said name should NOT be stored into, as it is undergoing
    a write operation.
    """

    __tablename__ = 'run_locks'

    name = Column(String, nullable=False, primary_key=True)
    locked_at = Column(DateTime, nullable=False)
    username = Column(String, nullable=True)

    def __init__(self, run_name, username=None):
        """Create a new lock for the given run name."""
        self.name = run_name
        self.locked_at = datetime.now()
        self.username = username

    def touch(self):
        """Update the lock's timestamp to be the current one."""
        self.locked_at = datetime.now()

    def when_expires(self, grace_seconds):
        """Calculates when the current lock will expire assuming the
        expiration time is grace_seconds, and the lock will never be touched
        until this moment."""
        return self.locked_at + timedelta(seconds=grace_seconds)

    def has_expired(self, grace_seconds):
        """Returns if the lock has expired, i.e. since the last touch()
        or creation, grace_seconds number of seconds has passed."""
        return datetime.now() > self.when_expires(grace_seconds)


class AnalyzerStatistic(Base):
    __tablename__ = 'analyzer_statistics'

    id = Column(Integer, autoincrement=True, primary_key=True)
    run_history_id = Column(Integer,
                            ForeignKey('run_histories.id',
                                       deferrable=True,
                                       initially="DEFERRED",
                                       ondelete='CASCADE'),
                            index=True)
    analyzer_type = Column(String)
    version = Column(Binary)
    successful = Column(Integer)
    failed = Column(Integer)
    failed_files = Column(Binary, nullable=True)

    def __init__(self, run_history_id, analyzer_type, version, successful,
                 failed, failed_files):
        self.run_history_id = run_history_id
        self.analyzer_type = analyzer_type
        self.version = version
        self.successful = successful
        self.failed = failed
        self.failed_files = failed_files


RunHistoryAnalysisInfo = Table(
    'run_history_analysis_info',
    Base.metadata,
    Column(
        'run_history_id',
        Integer,
        ForeignKey('run_histories.id',
                   deferrable=True,
                   initially="DEFERRED",
                   ondelete="CASCADE"),
        index=True),
    Column('analysis_info_id', Integer, ForeignKey('analysis_info.id'))
)


class RunHistory(Base):
    __tablename__ = 'run_histories'

    id = Column(Integer, autoincrement=True, primary_key=True)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True,
                               initially="DEFERRED", ondelete='CASCADE'),
                    index=True)
    version_tag = Column(String)
    user = Column(String, nullable=False)
    time = Column(DateTime, nullable=False)
    cc_version = Column(String, nullable=True)
    description = Column(String, nullable=True)

    run = relationship(Run, uselist=False)
    analyzer_statistics = relationship(AnalyzerStatistic,
                                       lazy="joined")

    analysis_info = relationship(
        "AnalysisInfo",
        secondary=RunHistoryAnalysisInfo)

    __table_args__ = (UniqueConstraint('run_id', 'version_tag'),)

    def __init__(self, run_id, version_tag, user, time, cc_version,
                 description):
        self.run_id = run_id
        self.version_tag = version_tag
        self.user = user
        self.time = time
        self.cc_version = cc_version
        self.description = description


class FileContent(Base):
    __tablename__ = 'file_contents'

    content_hash = Column(String, primary_key=True)
    content = Column(Binary)

    # Note: two different authors can commit the same file content to
    # different paths in which case the blame info will be the same.
    blame_info = Column(Binary, nullable=True)

    def __init__(self, content_hash, content, blame_info):
        self.content_hash, self.content, self.blame_info = \
            content_hash, content, blame_info


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, autoincrement=True, primary_key=True)
    filepath = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    content_hash = Column(String,
                          ForeignKey('file_contents.content_hash',
                                     deferrable=True,
                                     initially="DEFERRED", ondelete='CASCADE'),
                          index=True)
    remote_url = Column(String, nullable=True)
    tracking_branch = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint('filepath', 'content_hash'),)

    def __init__(self, filepath, content_hash, remote_url, tracking_branch):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.content_hash = content_hash
        self.remote_url = remote_url
        self.tracking_branch = tracking_branch


class BugPathEvent(Base):
    __tablename__ = 'bug_path_events'

    line_begin = Column(Integer)
    col_begin = Column(Integer)
    line_end = Column(Integer)
    col_end = Column(Integer)

    order = Column(Integer, primary_key=True)

    msg = Column(String)
    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'), index=True)
    report_id = Column(Integer, ForeignKey('reports.id', deferrable=True,
                                           initially="DEFERRED",
                                           ondelete='CASCADE'),
                       index=True,
                       primary_key=True)

    def __init__(self, line_begin, col_begin, line_end, col_end,
                 order, msg, file_id, report_id):
        self.line_begin, self.col_begin, self.line_end, self.col_end = \
            line_begin, col_begin, line_end, col_end

        self.order = order
        self.msg = msg
        self.file_id = file_id
        self.report_id = report_id


class BugReportPoint(Base):
    __tablename__ = 'bug_report_points'

    line_begin = Column(Integer)
    col_begin = Column(Integer)
    line_end = Column(Integer)
    col_end = Column(Integer)

    order = Column(Integer, primary_key=True)

    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'), index=True)
    report_id = Column(Integer, ForeignKey('reports.id', deferrable=True,
                                           initially="DEFERRED",
                                           ondelete='CASCADE'),
                       index=True,
                       primary_key=True)

    def __init__(self, line_begin, col_begin, line_end, col_end,
                 order, file_id, report_id):
        self.line_begin, self.col_begin, self.line_end, self.col_end = \
            line_begin, col_begin, line_end, col_end

        self.order = order
        self.file_id = file_id
        self.report_id = report_id


class ExtendedReportData(Base):
    """
    Store extra information which can help to understand or fix a report.
    """
    __tablename__ = 'extended_report_data'

    id = Column(Integer, autoincrement=True, primary_key=True)

    report_id = Column(Integer, ForeignKey('reports.id', deferrable=True,
                                           initially="DEFERRED",
                                           ondelete='CASCADE'),
                       index=True)

    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'), index=True)

    type = Column(Enum('note',
                       'macro',
                       'fixit',
                       name='extended_data_type'))

    line_begin = Column(Integer)
    col_begin = Column(Integer)
    line_end = Column(Integer)
    col_end = Column(Integer)

    message = Column(String)

    def __init__(self, line_begin, col_begin, line_end, col_end,
                 message, file_id, report_id, data_type):

        self.line_begin = line_begin
        self.col_begin = col_begin
        self.line_end = line_end
        self.col_end = col_end
        self.message = message
        self.file_id = file_id
        self.report_id = report_id
        self.type = data_type


ReportAnalysisInfo = Table(
    'report_analysis_info',
    Base.metadata,
    Column(
        'report_id',
        Integer,
        ForeignKey('reports.id',
                   deferrable=True,
                   initially="DEFERRED",
                   ondelete="CASCADE"),
        index=True),
    Column('analysis_info_id', Integer, ForeignKey('analysis_info.id'))
)


ReviewStatusType = Enum(
    'unreviewed',
    'confirmed',
    'false_positive',
    'intentional',
    name='review_status')


class Report(Base):
    __tablename__ = 'reports'

    id = Column(Integer, autoincrement=True, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'),
                     index=True)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True,
                               initially="DEFERRED",
                               ondelete='CASCADE'),
                    index=True)
    bug_id = Column(String, index=True)
    checker_id = Column(String)
    checker_cat = Column(String)
    bug_type = Column(String)
    severity = Column(Integer)
    line = Column(Integer)
    column = Column(Integer)
    path_length = Column(Integer)
    analyzer_name = Column(String,
                           nullable=False,
                           server_default="unknown")

    # TODO: multiple messages to multiple source locations?
    checker_message = Column(String)
    detection_status = Column(Enum('new',
                                   'unresolved',
                                   'resolved',
                                   'reopened',
                                   'off',
                                   'unavailable',
                                   name='detection_status'))
    review_status = Column(ReviewStatusType,
                           nullable=False,
                           server_default='unreviewed')
    review_status_author = Column(String)
    review_status_message = Column(Binary)
    review_status_date = Column(DateTime, nullable=True)
    # We'd like to indicate whether a suppression comes from a source code
    # comment or set via the GUI. Former ones must not change when set from
    # GUI.
    review_status_is_in_source = Column(
        Boolean, nullable=False, server_default=false())

    detected_at = Column(DateTime, nullable=False)

    # A report is considered as "fixed" when it is not found in the project
    # anymore either based on its detection status or its review status is set
    # to false positive or intentional.
    fixed_at = Column(DateTime)

    analysis_info = relationship(
        "AnalysisInfo",
        secondary=ReportAnalysisInfo)

    # Cascade delete might remove rows, SQLAlchemy warns about this.
    # To remove warnings about already deleted items set this to False.
    __mapper_args__ = {
        'confirm_deleted_rows': False
    }

    # Priority/severity etc...
    def __init__(self, run_id, bug_id, file_id, checker_message, checker_id,
                 checker_cat, bug_type, line, column, severity, review_status,
                 review_status_author, review_status_message,
                 review_status_date, review_status_is_in_source,
                 detection_status, detection_date, path_length,
                 analyzer_name=None):
        self.run_id = run_id
        self.file_id = file_id
        self.bug_id = bug_id
        self.checker_message = checker_message
        self.severity = severity
        self.checker_id = checker_id
        self.checker_cat = checker_cat
        self.bug_type = bug_type
        self.review_status = review_status
        self.review_status_author = review_status_author
        self.review_status_message = review_status_message
        self.review_status_date = review_status_date
        self.review_status_is_in_source = review_status_is_in_source
        self.detection_status = detection_status
        self.line = line
        self.column = column
        self.detected_at = detection_date
        self.path_length = path_length
        self.analyzer_name = analyzer_name


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, autoincrement=True, primary_key=True)
    bug_hash = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False)
    message = Column(Binary, nullable=False)

    # Default value is 0 which means a user given comment.
    kind = Column(Integer,
                  nullable=False,
                  server_default="0")

    created_at = Column(DateTime, nullable=False)

    def __init__(self, bug_hash, author, message, kind, created_at):
        self.bug_hash = bug_hash
        self.author = author
        self.message = message
        self.kind = kind
        self.created_at = created_at


class ReviewStatus(Base):
    """
    This table contains a mapping from bug hashes to review statuses. This
    mapping determines the default review status of a newly added report which
    doesn't have a review status source code comment. In case of no source code
    comment and no entry in this table the default review status is
    "unreviewed".
    """
    __tablename__ = 'review_statuses'

    bug_hash = Column(String, primary_key=True)
    status = Column(ReviewStatusType, nullable=False)
    author = Column(String, nullable=False)
    message = Column(Binary, nullable=False)
    date = Column(DateTime, nullable=False)


class SourceComponent(Base):
    __tablename__ = 'source_components'

    name = Column(String, nullable=False, primary_key=True)

    # Contains multiple file paths separated by new line characters. Each file
    # path start with a '+' (path should be filtered) or '-' (path should not
    # be filtered) sign. E.g.: "+/a/b/x.cpp\n-/a/b/"
    value = Column(Binary, nullable=False)

    description = Column(Text, nullable=True)
    username = Column(String, nullable=True)

    def __init__(self, name, value, description=None, user_name=None):
        self.name = name
        self.value = value
        self.description = description
        self.username = user_name


class CleanupPlan(Base):
    __tablename__ = 'cleanup_plans'

    __table_args__ = (
        UniqueConstraint('name'),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    def __init__(self, name, due_date=None, description=None, closed_at=None):
        self.name = name
        self.due_date = due_date
        self.description = description
        self.closed_at = closed_at


class CleanupPlanReportHash(Base):
    __tablename__ = 'cleanup_plan_report_hashes'

    cleanup_plan_id = Column(
        Integer,
        ForeignKey('cleanup_plans.id',
                   deferrable=True,
                   initially="DEFERRED",
                   ondelete="CASCADE"),
        index=True)

    bug_hash = Column(String, primary_key=True)


IDENTIFIER = {
    'identifier': "RunDatabase",
    'orm_meta': CC_META
}
