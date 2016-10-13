# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
ORM model.
"""
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime
from math import ceil

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
from sqlalchemy.sql.expression import true

CC_META = MetaData(naming_convention={
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

# Create base class for ORM classes.
Base = declarative_base(metadata=CC_META)


# Start of ORM classes.

class DBVersion(Base):
    __tablename__ = 'db_version'
    # TODO: constraint, only one line in this table
    major = Column(Integer, primary_key=True)
    minor = Column(Integer, primary_key=True)

    def __init__(self, major, minor):
        self.major = major
        self.minor = minor


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
    command = Column(String)
    inc_count = Column(Integer)
    can_delete = Column(Boolean, nullable=False, server_default=true(),
                        default=True)

    # Relationships (One to Many).
    configlist = relationship('Config', cascade="all, delete-orphan",
                              passive_deletes=True)
    buildactionlist = relationship('BuildAction', cascade="all, delete-orphan",
                                   passive_deletes=True)

    def __init__(self, name, version, command):
        self.date, self.name, self.version, self.command = \
            datetime.now(), name, version, command
        self.duration = -1
        self.inc_count = 0

    def mark_finished(self):
        self.duration = ceil((datetime.now() - self.date).total_seconds())


class Config(Base):
    __tablename__ = 'configs'

    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True, initially="DEFERRED",
                               ondelete='CASCADE'), primary_key=True)
    checker_name = Column(String, primary_key=True)
    attribute = Column(String, primary_key=True)
    value = Column(String, primary_key=True)

    def __init__(self, run_id, checker_name, attribute, value):
        self.attribute, self.value = attribute, value
        self.checker_name, self.run_id = checker_name, run_id


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, autoincrement=True, primary_key=True)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True, initially="DEFERRED",
                               ondelete='CASCADE'))
    filepath = Column(String)
    content = Column(Binary)
    inc_count = Column(Integer)

    def __init__(self, run_id, filepath):
        self.run_id, self.filepath = run_id, filepath
        self.inc_count = 0

    def addContent(self, content):
        self.content = content


class BuildAction(Base):
    __tablename__ = 'build_actions'

    id = Column(Integer, autoincrement=True, primary_key=True)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True, initially="DEFERRED",
                               ondelete='CASCADE'))
    build_cmd = Column(String)
    analyzer_type = Column(String, nullable=False)
    analyzed_source_file = Column(String, nullable=False)
    check_cmd = Column(String)
    # No failure if the text is empty.
    failure_txt = Column(String)
    date = Column(DateTime)

    # Seconds, -1 if unfinished.
    duration = Column(Integer)

    def __init__(self, run_id, build_cmd, check_cmd, analyzer_type,
                 analyzed_source_file):
        self.run_id, self.build_cmd, self.check_cmd, self.failure_txt = \
            run_id, build_cmd, check_cmd, ''
        self.date = datetime.now()
        self.analyzer_type = analyzer_type
        self.analyzed_source_file = analyzed_source_file
        self.duration = -1

    def mark_finished(self, failure_txt):
        self.failure_txt = failure_txt
        self.duration = (datetime.now() - self.date).total_seconds()


class BugPathEvent(Base):
    __tablename__ = 'bug_path_events'

    id = Column(Integer, autoincrement=True, primary_key=True)
    line_begin = Column(Integer)
    col_begin = Column(Integer)
    line_end = Column(Integer)
    col_end = Column(Integer)
    msg = Column(String)
    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'), index=True)

    next = Column(Integer)
    prev = Column(Integer)

    def __init__(self, line_begin, col_begin, line_end, col_end, msg, file_id):
        self.line_begin, self.col_begin, self.line_end, self.col_end = \
            line_begin, col_begin, line_end, col_end
        self.file_id, self.msg = file_id, msg

    def addPrev(self, prev):
        self.prev = prev

    def addNext(self, next):
        self.next = next

    def isLast(self):
        return self.next is None

    def isFirst(self):
        return self.prev is None


class BugReportPoint(Base):
    __tablename__ = 'bug_report_points'

    id = Column(Integer, autoincrement=True, primary_key=True)
    line_begin = Column(Integer)
    col_begin = Column(Integer)
    line_end = Column(Integer)
    col_end = Column(Integer)
    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'), index=True)

    # TODO: Add check, the value must be an existing id or null.
    # Be careful when inserting.
    next = Column(Integer)

    def __init__(self, line_begin, col_begin, line_end, col_end, file_id):
        self.line_begin, self.col_begin, self.line_end, self.col_end = \
            line_begin, col_begin, line_end, col_end
        self.file_id = file_id

    def addNext(self, next):
        self.next = next

    def isLast(self):
        return self.next is None


class Report(Base):
    __tablename__ = 'reports'

    id = Column(Integer, autoincrement=True, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'))
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True, initially="DEFERRED",
                               ondelete='CASCADE'), index=True)
    bug_id = Column(String, index=True)
    checker_id = Column(String)
    checker_cat = Column(String)
    bug_type = Column(String)
    severity = Column(Integer)

    # TODO: multiple messages to multiple source locations?
    checker_message = Column(String)
    start_bugpoint = Column(Integer,
                            ForeignKey('bug_report_points.id', deferrable=True,
                                       initially="DEFERRED",
                                       ondelete='CASCADE'))

    start_bugevent = Column(Integer,
                            ForeignKey('bug_path_events.id', deferrable=True,
                                       initially="DEFERRED",
                                       ondelete='CASCADE'), index=True)
    end_bugevent = Column(Integer,
                          ForeignKey('bug_path_events.id', deferrable=True,
                                     initially="DEFERRED", ondelete='CASCADE'),
                          index=True)
    suppressed = Column(Boolean)

    # Cascade delete might remove rows SQLAlchemy warns about this
    # to remove warnings about already deleted items set this to False.
    __mapper_args__ = {
        'confirm_deleted_rows': False
    }

    # Priority/severity etc...
    def __init__(self, run_id, bug_id, file_id, checker_message, start_bugpoint,
                 start_bugevent, end_bugevent, checker_id, checker_cat,
                 bug_type, severity, suppressed):
        self.run_id = run_id
        self.file_id = file_id
        self.bug_id, self.checker_message = bug_id, checker_message
        self.start_bugpoint = start_bugpoint
        self.start_bugevent = start_bugevent
        self.end_bugevent = end_bugevent
        self.severity = severity
        self.checker_id, self.checker_cat = checker_id, checker_cat
        self.suppressed, self.bug_type = suppressed, bug_type


class ReportsToBuildActions(Base):
    __tablename__ = 'reports_to_build_actions'

    report_id = Column(Integer, ForeignKey('reports.id', deferrable=True,
                                           initially="DEFERRED",
                                           ondelete='CASCADE'),
                       primary_key=True)
    build_action_id = Column(
        Integer,
        ForeignKey('build_actions.id', deferrable=True, initially="DEFERRED",
                   ondelete='CASCADE'), primary_key=True)

    def __init__(self, report_id, build_action_id):
        self.report_id = report_id
        self.build_action_id = build_action_id


class SuppressBug(Base):
    __tablename__ = 'suppress_bug'

    id = Column(Integer, autoincrement=True, primary_key=True)
    hash = Column(String, nullable=False)
    file_name = Column(String)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True, initially="DEFERRED",
                               ondelete='CASCADE'), nullable=False)
    comment = Column(Binary)

    def __init__(self, run_id, hash, file_name, comment):
        self.hash, self.run_id = hash, run_id
        self.comment = comment
        self.file_name = file_name


class SkipPath(Base):
    __tablename__ = 'skip_path'

    id = Column(Integer, autoincrement=True, primary_key=True)
    path = Column(String)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True, initially="DEFERRED",
                               ondelete='CASCADE'), nullable=False)
    comment = Column(Binary)

    def __init__(self, run_id, path, comment):
        self.path = path
        self.run_id = run_id
        self.comment = comment


# End of ORM classes.


def CreateSchema(engine):
    """ Creates the schema if it does not exists.
        Do not check version or do migration yet. """
    Base.metadata.create_all(engine)


def CreateSession(engine):
    """ Creates a scoped session factory that can act like a session.
        The factory uses a thread_local registry, so every thread have
        its own session. """
    SessionFactory = scoped_session(sessionmaker(bind=engine))
    return SessionFactory
