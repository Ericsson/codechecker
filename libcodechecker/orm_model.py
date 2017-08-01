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
                    ForeignKey('runs.id', deferrable=True,
                               initially="DEFERRED", ondelete='CASCADE'),
                    primary_key=True)
    checker_name = Column(String, primary_key=True)
    attribute = Column(String, primary_key=True)
    value = Column(String, primary_key=True)

    def __init__(self, run_id, checker_name, attribute, value):
        self.attribute, self.value = attribute, value
        self.checker_name, self.run_id = checker_name, run_id


class FileContent(Base):
    __tablename__ = 'file_contents'

    content_hash = Column(String, primary_key=True)
    content = Column(Binary)

    def __init__(self, content_hash, content):
        self.content_hash, self.content = content_hash, content


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, autoincrement=True, primary_key=True)
    filepath = Column(String)
    content_hash = Column(String,
                          ForeignKey('file_contents.content_hash',
                                     deferrable=True,
                                     initially="DEFERRED", ondelete='CASCADE'))

    __table_args__ = (UniqueConstraint('filepath', 'content_hash'),)

    def __init__(self, filepath, content_hash):
        self.filepath, self.content_hash = filepath, content_hash


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
                       primary_key=True)

    def __init__(self, line_begin, col_begin, line_end, col_end,
                 order, file_id, report_id):
        self.line_begin, self.col_begin, self.line_end, self.col_end = \
            line_begin, col_begin, line_end, col_end

        self.order = order
        self.file_id = file_id
        self.report_id = report_id


class Report(Base):
    __tablename__ = 'reports'

    id = Column(Integer, autoincrement=True, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id', deferrable=True,
                                         initially="DEFERRED",
                                         ondelete='CASCADE'))
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

    # TODO: multiple messages to multiple source locations?
    checker_message = Column(String)
    suppressed = Column(Boolean)

    # Cascade delete might remove rows SQLAlchemy warns about this
    # to remove warnings about already deleted items set this to False.
    __mapper_args__ = {
        'confirm_deleted_rows': False
    }

    # Priority/severity etc...
    def __init__(self, run_id, bug_id, file_id, checker_message, checker_id,
                 checker_cat, bug_type, severity, suppressed):
        self.run_id = run_id
        self.file_id = file_id
        self.bug_id = bug_id
        self.checker_message = checker_message
        self.severity = severity
        self.checker_id = checker_id
        self.checker_cat = checker_cat
        self.suppressed = suppressed
        self.bug_type = bug_type


class SuppressBug(Base):
    __tablename__ = 'suppress_bug'

    id = Column(Integer, autoincrement=True, primary_key=True)
    hash = Column(String, nullable=False)
    file_name = Column(String)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True,
                               initially="DEFERRED",
                               ondelete='CASCADE'),
                    nullable=False)
    comment = Column(Binary)

    def __init__(self, run_id, hash, file_name, comment):
        self.hash, self.run_id = hash, run_id
        self.comment = comment.encode('utf8')
        self.file_name = file_name


class SkipPath(Base):
    __tablename__ = 'skip_path'

    id = Column(Integer, autoincrement=True, primary_key=True)
    path = Column(String)
    run_id = Column(Integer,
                    ForeignKey('runs.id', deferrable=True,
                               initially="DEFERRED",
                               ondelete='CASCADE'),
                    nullable=False)
    comment = Column(Binary)

    def __init__(self, run_id, path, comment):
        self.path = path
        self.run_id = run_id
        self.comment = comment


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, autoincrement=True, primary_key=True)
    bug_hash = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False)
    message = Column(Binary, nullable=False)
    created_at = Column(DateTime, nullable=False)

    def __init__(self, bug_hash, author, message, created_at):
        self.bug_hash = bug_hash
        self.author = author
        self.message = message
        self.created_at = created_at


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
