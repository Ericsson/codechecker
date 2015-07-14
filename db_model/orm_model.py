# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
orm model
'''
from __future__ import print_function
from __future__ import unicode_literals

from sqlalchemy import *
from sqlalchemy.orm import *

from sqlalchemy.ext.declarative import declarative_base

from datetime import *

# Create base class for ORM classes
Base = declarative_base()

# Start of ORM classes

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

    id = Column(Integer, Sequence('run_id_seq'), primary_key=True)
    date = Column(DateTime)
    duration = Column(Integer)  # Seconds, -1 if unfinished
    name = Column(String)
    version = Column(String)
    command = Column(String)
    inc_count = Column(Integer)

    # Relationships (One to Many)
    configlist = relationship('Config', cascade="all, delete-orphan")
    buildactionlist = relationship('BuildAction', cascade="all, delete-orphan")

    def __init__(self, name, version, command):
        self.date, self.name, self.version, self.command = \
            datetime.now(), name, version, command
        self.duration = -1
        self.inc_count = 0

    def mark_finished(self):
        self.duration = (datetime.now() - self.date).total_seconds()


class Config(Base):
    __tablename__ = 'configs'

    run_id = Column(Integer, ForeignKey('runs.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), primary_key=True)
    checker_name = Column(String, primary_key=True)
    attribute = Column(String, primary_key=True)
    value = Column(String, primary_key=True)

    def __init__(self, run_id, checker_name, attribute, value):
        self.attribute, self.value = attribute, value
        self.checker_name, self.run_id = checker_name, run_id

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, Sequence('file_id_seq'), primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'))
    filepath = Column(String)
    content = Column(Binary)
    inc_count = Column(Integer)

    # TODO: constraint: (filepath, run_id) is unique

    def __init__(self, run_id, filepath):
        self.run_id, self.filepath = run_id, filepath
        self.inc_count = 0

    def addContent(self, content):
        self.content = content


class BuildAction(Base):
    __tablename__ = 'build_actions'

    id = Column(Integer, Sequence('build_action_id_seq'), primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'))
    build_cmd = Column(String)
    check_cmd = Column(String)
    # No failure if the text is empty
    failure_txt = Column(String)
    date = Column(DateTime)

    # Seconds, -1 if unfinished
    duration = Column(Integer)

    build_target = Column(String)

    # Relationships (One to Many)
    # plistlist = relationship('Plist')

    def __init__(self, run_id, build_cmd, check_cmd, build_target):
        self.run_id, self.build_cmd, self.check_cmd, self.failure_txt = \
            run_id, build_cmd, check_cmd, ''
        self.date = datetime.now()
        self.duration = -1
        self.build_target = build_target

    def mark_finished(self, failure_txt):
        self.failure_txt = failure_txt
        self.duration = (datetime.now() - self.date).total_seconds()


class BugPathEvent(Base):
    __tablename__ = 'bug_path_events'

    id = Column(Integer, Sequence('bug_path_event_id_seq'), primary_key=True)
    line_begin = Column(Integer)
    col_begin = Column(Integer)
    line_end = Column(Integer)
    col_end = Column(Integer)
    msg = Column(String)
    file_id = Column(Integer, ForeignKey('files.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), index = True)

    next = Column(Integer)
    prev = Column(Integer)

    def __init__(self, line_begin, col_begin, line_end, col_end, msg, file_id):
        self.line_begin, self.col_begin, self.line_end, self.col_end, self.msg = \
            line_begin, col_begin, line_end, col_end, msg
        self.file_id = file_id

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

    id = Column(Integer, Sequence('report_point_id_seq'), primary_key=True)
    line_begin = Column(Integer)
    col_begin = Column(Integer)
    line_end = Column(Integer)
    col_end = Column(Integer)
    file_id = Column(Integer, ForeignKey('files.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), index = True)

    # TODO: Add check, the value must be an existing id or null
    # be careful when inserting
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
    __table_args__ = (UniqueConstraint('run_id', 'bug_id'), )

    id = Column(Integer, Sequence('report_id_seq'), primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'))
    run_id = Column(Integer, ForeignKey('runs.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), index = True)
    # build_action_id = Column(Integer, ForeignKey('build_actions.id', deferrable = True, initially = "DEFERRED"))
    bug_id = Column(String, index = True)
    bug_id_type = Column(Integer)
    checker_id = Column(String)
    checker_cat = Column(String)
    bug_type = Column(String)
    severity = Column(Integer)

    # TODO: multiple messages to multiple source locations?
    checker_message = Column(String)
    start_bugpoint = Column(Integer, ForeignKey('bug_report_points.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'))

    start_bugevent = Column(Integer, ForeignKey('bug_path_events.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'))
    end_bugevent = Column(Integer, ForeignKey('bug_path_events.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'))
    suppressed = Column(Boolean)


    # Priority/severity etc...
    def __init__(self, run_id, bug_id, bug_id_type, file_id, checker_message, start_bugpoint, start_bugevent, end_bugevent, checker_id, checker_cat, bug_type, severity, suppressed):
        self.run_id = run_id
        self.file_id = file_id
        self.bug_id, self.bug_id_type, self.checker_message = bug_id, bug_id_type, checker_message
        self.start_bugpoint = start_bugpoint
        self.start_bugevent = start_bugevent
        self.end_bugevent = end_bugevent
        self.severity = severity
        self.checker_id, self.checker_cat, self.bug_type = checker_id, checker_cat, bug_type
        self.suppressed = suppressed

class ReportsToBuildActions(Base):
    __tablename__ = 'reports_to_build_actions'

    report_id = Column(Integer, ForeignKey('reports.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), primary_key=True)
    build_action_id = Column(
        Integer, ForeignKey('build_actions.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), primary_key=True)

    def __init__(self, report_id, build_action_id):
        self.report_id, self.build_action_id = report_id, build_action_id


class SuppressBug(Base):
    __tablename__ = 'suppress_bug'

    hash = Column(String, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), primary_key=True)
    type = Column(Integer)
    comment = Column(Binary)

    def __init__(self, run_id, hash, type, comment):
        self.hash, self.run_id = hash, run_id
        self.type, self.comment = type, comment


class SkipPath(Base):
    __tablename__ = 'skip_path'

    path = Column(String, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), primary_key=True)
    comment = Column(Binary)

    def __init__(self, run_id, path, comment):
        self.path, self.run_id = path, run_id
        self.comment = comment


class ModuleToReport(Base):
    __tablename__ = 'modules_to_reports'

    report_id = Column(Integer, ForeignKey('reports.id', deferrable = True, initially = "DEFERRED", ondelete='CASCADE'), primary_key=True)
    run_id = Column(Integer)
    module = Column(String)

    def __init__(self, run_id, module, report_id):
        self.module, self.report_id = module, report_id
        self.run_id = run_id

# End of ORM classes


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
