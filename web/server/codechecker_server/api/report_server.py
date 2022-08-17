# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handle Thrift requests.
"""

import base64
import html
import json
import os
import re
import shlex
import stat
import time
import zlib

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import sqlalchemy
from sqlalchemy.sql.expression import or_, and_, not_, func, \
    asc, desc, union_all, select, bindparam, literal_column, cast

import codechecker_api_shared
from codechecker_api.codeCheckerDBAccess_v6 import constants, ttypes
from codechecker_api.codeCheckerDBAccess_v6.ttypes import AnalysisInfoFilter, \
    BlameData, BlameInfo, BugPathPos, CheckerCount, Commit, CommitAuthor, \
    CommentData, DiffType, Encoding, RunHistoryData, Order, ReportData, \
    ReportDetails, ReviewData, ReviewStatusRule, ReviewStatusRuleFilter, \
    ReviewStatusRuleSortMode, ReviewStatusRuleSortType, RunData, RunFilter, \
    RunReportCount, RunSortType, RunTagCount, SourceComponentData, \
    SourceFileData, SortMode, SortType, ExportData

from codechecker_common import util
from codechecker_common.logger import get_logger

from codechecker_web.shared import webserver_context
from codechecker_web.shared import convert

from codechecker_server.profiler import timeit

from .. import permissions
from ..database import db_cleanup
from ..database.config_db_model import Product
from ..database.database import conv, DBSession, escape_like
from ..database.run_db_model import \
    AnalysisInfo, AnalyzerStatistic, BugPathEvent, BugReportPoint, \
    CleanupPlan, CleanupPlanReportHash, Comment, ExtendedReportData, File, \
    FileContent, Report, ReportAnalysisInfo, ReviewStatus, Run, RunHistory, \
    RunHistoryAnalysisInfo, RunLock, SourceComponent

from .thrift_enum_helper import detection_status_enum, \
    detection_status_str, review_status_enum, review_status_str, \
    report_extended_data_type_enum


LOG = get_logger('server')

GEN_OTHER_COMPONENT_NAME = "Other (auto-generated)"

SQLITE_MAX_VARIABLE_NUMBER = 999
SQLITE_MAX_COMPOUND_SELECT = 500


class CommentKindValue:
    USER = 0
    SYSTEM = 1


def comment_kind_from_thrift_type(kind):
    """ Convert the given comment kind from Thrift type to Python enum. """
    if kind == ttypes.CommentKind.USER:
        return CommentKindValue.USER
    elif kind == ttypes.CommentKind.SYSTEM:
        return CommentKindValue.SYSTEM


def comment_kind_to_thrift_type(kind):
    """ Convert the given comment kind from Python enum to Thrift type. """
    if kind == CommentKindValue.USER:
        return ttypes.CommentKind.USER
    elif kind == CommentKindValue.SYSTEM:
        return ttypes.CommentKind.SYSTEM


def verify_limit_range(limit):
    """Verify limit value for the queries.

    Query limit should not be larger than the max allowed value.
    Max is returned if the value is larger than max.
    """
    max_query_limit = constants.MAX_QUERY_SIZE
    if not limit:
        return max_query_limit
    if limit > max_query_limit:
        LOG.warning('Query limit %d was larger than max query limit %d, '
                    'setting limit to %d',
                    limit,
                    max_query_limit,
                    max_query_limit)
        limit = max_query_limit
    return limit


def slugify(text):
    """
    Removes and replaces special characters in a given text.
    """
    # Removes non-alpha characters.
    norm_text = re.sub(r'[^\w\s\-/]', '', text)

    # Converts spaces and slashes to underscores.
    norm_text = re.sub(r'([\s]+|[/]+)', '_', norm_text)

    return norm_text


def exc_to_thrift_reqfail(func):
    """
    Convert internal exceptions to RequestFailed exception
    which can be sent back on the thrift connections.
    """
    func_name = func.__name__

    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            return res

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            # Convert SQLAlchemy exceptions.
            msg = str(alchemy_ex)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)
        except codechecker_api_shared.ttypes.RequestFailed as rf:
            LOG.warning("%s:\n%s", func_name, rf.message)
            raise
        except Exception as ex:
            import traceback
            traceback.print_exc()
            msg = str(ex)
            LOG.warning("%s:\n%s", func_name, msg)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL, msg)

    return wrapper


def get_component_values(
    session: DBSession,
    component_name: str
) -> Tuple[List[str], List[str]]:
    """
    Get component values by component names and returns a tuple where the
    first item contains a list path which should be skipped and the second
    item contains a list of path which should be included.
    E.g.:
      +/a/b/x.cpp
      +/a/b/y.cpp
      -/a/b
    On the above component value this function will return the following:
      (['/a/b'], ['/a/b/x.cpp', '/a/b/y.cpp'])
    """
    components = session.query(SourceComponent) \
        .filter(SourceComponent.name.like(component_name)) \
        .all()

    skip = []
    include = []

    for component in components:
        values = component.value.decode('utf-8').split('\n')
        for value in values:
            value = value.strip()
            if not value:
                continue

            v = value[1:]
            if value[0] == '+':
                include.append(v)
            elif value[0] == '-':
                skip.append(v)

    return skip, include


def process_report_filter(session, run_ids, report_filter, cmp_data=None):
    """
    Process the new report filter.
    """
    AND = []

    cmp_filter_expr, join_tables = process_cmp_data_filter(
        session, run_ids, report_filter, cmp_data)

    if cmp_filter_expr is not None:
        AND.append(cmp_filter_expr)

    if report_filter is None:
        return and_(*AND), join_tables

    if report_filter.reportHash == []:
        return and_(False), []

    if report_filter.filepath:
        OR = [File.filepath.ilike(conv(fp))
              for fp in report_filter.filepath]

        AND.append(or_(*OR))
        join_tables.append(File)

    if report_filter.checkerMsg:
        OR = [Report.checker_message.ilike(conv(cm))
              for cm in report_filter.checkerMsg]
        AND.append(or_(*OR))

    if report_filter.checkerName:
        OR = [Report.checker_id.ilike(conv(cn))
              for cn in report_filter.checkerName]
        AND.append(or_(*OR))

    if report_filter.analyzerNames:
        OR = [Report.analyzer_name.ilike(conv(an))
              for an in report_filter.analyzerNames]
        AND.append(or_(*OR))

    if report_filter.runName:
        OR = [Run.name.ilike(conv(rn))
              for rn in report_filter.runName]
        AND.append(or_(*OR))
        join_tables.append(Run)

    if report_filter.reportHash:
        OR = []
        no_joker = []

        for rh in report_filter.reportHash:
            if '*' in rh:
                OR.append(Report.bug_id.ilike(conv(rh)))
            else:
                no_joker.append(rh)

        if no_joker:
            OR.append(Report.bug_id.in_(no_joker))

        AND.append(or_(*OR))

    if report_filter.cleanupPlanNames:
        OR = []
        for cleanup_plan_name in report_filter.cleanupPlanNames:
            q = select([CleanupPlanReportHash.bug_hash]) \
                .where(
                    CleanupPlanReportHash.cleanup_plan_id.in_(
                        select([CleanupPlan.id])
                        .where(CleanupPlan.name == cleanup_plan_name)
                        .distinct()
                    )) \
                .distinct()

            OR.append(Report.bug_id.in_(q))

        AND.append(or_(*OR))

    if report_filter.severity:
        AND.append(Report.severity.in_(report_filter.severity))

    if report_filter.detectionStatus:
        dst = list(map(detection_status_str,
                       report_filter.detectionStatus))
        AND.append(Report.detection_status.in_(dst))

    if report_filter.reviewStatus:
        OR = [Report.review_status.in_(
            list(map(review_status_str, report_filter.reviewStatus)))]
        AND.append(or_(*OR))

    if report_filter.firstDetectionDate is not None:
        date = datetime.fromtimestamp(report_filter.firstDetectionDate)
        AND.append(Report.detected_at >= date)

    if report_filter.fixDate is not None:
        date = datetime.fromtimestamp(report_filter.fixDate)
        AND.append(Report.detected_at < date)

    if report_filter.date:
        detected_at = report_filter.date.detected
        if detected_at:
            if detected_at.before:
                detected_before = datetime.fromtimestamp(detected_at.before)
                AND.append(Report.detected_at <= detected_before)

            if detected_at.after:
                detected_after = datetime.fromtimestamp(detected_at.after)
                AND.append(Report.detected_at >= detected_after)

        fixed_at = report_filter.date.fixed
        if fixed_at:
            if fixed_at.before:
                fixed_before = datetime.fromtimestamp(fixed_at.before)
                AND.append(Report.fixed_at <= fixed_before)

            if fixed_at.after:
                fixed_after = datetime.fromtimestamp(fixed_at.after)
                AND.append(Report.fixed_at >= fixed_after)

    if report_filter.runHistoryTag:
        OR = []
        for history_date in report_filter.runHistoryTag:
            date = datetime.strptime(history_date,
                                     '%Y-%m-%d %H:%M:%S.%f')
            OR.append(and_(Report.detected_at <= date, or_(
                Report.fixed_at.is_(None), Report.fixed_at >= date)))
        AND.append(or_(*OR))

    if report_filter.componentNames:
        AND.append(process_source_component_filter(
            session, report_filter.componentNames))
        join_tables.append(File)

    if report_filter.bugPathLength is not None:
        min_path_length = report_filter.bugPathLength.min
        if min_path_length is not None:
            AND.append(Report.path_length >= min_path_length)

        max_path_length = report_filter.bugPathLength.max
        if max_path_length is not None:
            AND.append(Report.path_length <= max_path_length)

    filter_expr = and_(*AND)
    return filter_expr, join_tables


def process_source_component_filter(session, component_names):
    """ Process source component filter.

    The virtual auto-generated Other component will be handled separately and
    the query part will be added to the filter.
    """
    OR = []

    for component_name in component_names:
        if component_name == GEN_OTHER_COMPONENT_NAME:
            file_query = get_other_source_component_file_query(session)
        else:
            file_query = get_source_component_file_query(session,
                                                         component_name)

        if file_query is not None:
            OR.append(file_query)

    return or_(*OR)


def filter_open_reports_in_tags(results, run_ids, tag_ids):
    """
    Adding filters on "results" query which filter on open reports in
    given runs and tags.
    """

    if run_ids:
        results = results.filter(Report.run_id.in_(run_ids))

    if tag_ids:
        results = results.outerjoin(
            RunHistory, RunHistory.run_id == Report.run_id) \
            .filter(RunHistory.id.in_(tag_ids)) \
            .filter(get_open_reports_date_filter_query())

    return results


def get_include_skip_queries(
    include: List[str],
    skip: List[str]
):
    """ Get queries for include and skip values of a component.

    To get the include and skip lists use the 'get_component_values' function.
    """
    include_q = select([File.id]) \
        .where(or_(*[
            File.filepath.like(conv(fp)) for fp in include])) \
        .distinct()

    skip_q = select([File.id]) \
        .where(or_(*[
            File.filepath.like(conv(fp)) for fp in skip])) \
        .distinct()

    return include_q, skip_q


def get_source_component_file_query(
    session: DBSession,
    component_name: str
):
    """ Get filter query for a single source component. """
    skip, include = get_component_values(session, component_name)

    if skip and include:
        include_q, skip_q = get_include_skip_queries(include, skip)
        return File.id.in_(include_q.except_(skip_q))
    elif include:
        return or_(*[File.filepath.like(conv(fp)) for fp in include])
    elif skip:
        return and_(*[not_(File.filepath.like(conv(fp))) for fp in skip])


def get_other_source_component_file_query(session):
    """ Get filter query for the auto-generated Others component.
    If there are no user defined source components in the database this
    function will return with None.

    The returned query will look like this:
        (Files NOT IN Component_1) AND (Files NOT IN Component_2) ... AND
        (Files NOT IN Component_N)
    """
    component_names = session.query(SourceComponent.name).all()

    # If there are no user defined source components we don't have to filter.
    if not component_names:
        return None

    def get_query(component_name: str):
        """ Get file filter query for auto generated Other component. """
        skip, include = get_component_values(session, component_name)

        if skip and include:
            include_q, skip_q = get_include_skip_queries(include, skip)
            return File.id.notin_(include_q.except_(skip_q))
        elif include:
            return and_(*[File.filepath.notlike(conv(fp)) for fp in include])
        elif skip:
            return or_(*[File.filepath.like(conv(fp)) for fp in skip])

    queries = [get_query(n) for (n, ) in component_names]
    return and_(*queries)


def get_open_reports_date_filter_query(tbl=Report, date=RunHistory.time):
    """ Get open reports date filter. """
    return and_(tbl.detected_at <= date,
                or_(tbl.fixed_at.is_(None),
                    tbl.fixed_at > date))


def get_diff_bug_id_query(session, run_ids, tag_ids, open_reports_date):
    """ Get bug id query for diff. """
    q = session.query(Report.bug_id.distinct())
    q = q.filter(Report.fixed_at.is_(None))
    if run_ids:
        q = q.filter(Report.run_id.in_(run_ids))

    if tag_ids:
        q = q.outerjoin(RunHistory,
                        RunHistory.run_id == Report.run_id) \
            .filter(RunHistory.id.in_(tag_ids)) \
            .filter(get_open_reports_date_filter_query())

    if open_reports_date:
        date = datetime.fromtimestamp(open_reports_date)

        q = q.filter(get_open_reports_date_filter_query(Report, date))

    return q


def get_diff_bug_id_filter(run_ids, tag_ids, open_reports_date):
    """ Get bug id filter for diff. """
    AND = []

    if run_ids:
        AND.append(Report.run_id.in_(run_ids))

    if tag_ids:
        AND.append(RunHistory.id.in_(tag_ids))
        AND.append(get_open_reports_date_filter_query())

    if open_reports_date:
        date = datetime.fromtimestamp(open_reports_date)
        AND.append(get_open_reports_date_filter_query(Report, date))

    return and_(*AND)


def get_diff_run_id_query(session, run_ids, tag_ids):
    """ Get run id query for diff. """
    q = session.query(Run.id.distinct())

    if run_ids:
        q = q.filter(Run.id.in_(run_ids))

    if tag_ids:
        q = q.outerjoin(RunHistory,
                        RunHistory.run_id == Run.id) \
            .filter(RunHistory.id.in_(tag_ids))

    return q


def is_cmp_data_empty(cmp_data):
    """ True if the parameter is None or no filter fields are set. """
    if not cmp_data:
        return True

    return not any([cmp_data.runIds,
                    cmp_data.runTag,
                    cmp_data.openReportsDate])


def is_baseline_empty(report_filter):
    """ True if the parameter is None or no baseline filter fields are set. """
    if not report_filter:
        return True

    return not any([report_filter.runTag,
                    report_filter.openReportsDate])


def process_cmp_data_filter(session, run_ids, report_filter, cmp_data):
    """ Process compare data filter. """
    base_tag_ids = report_filter.runTag if report_filter else None
    base_open_reports_date = report_filter.openReportsDate \
        if report_filter else None

    if is_cmp_data_empty(cmp_data):
        if not run_ids and is_baseline_empty(report_filter):
            return None, []

        diff_filter = get_diff_bug_id_filter(
            run_ids, base_tag_ids, base_open_reports_date)
        join_tables = []

        if run_ids:
            join_tables.append(Run)
        if base_tag_ids:
            join_tables.append(RunHistory)

        return and_(diff_filter), join_tables

    query_base = get_diff_bug_id_query(session, run_ids, base_tag_ids,
                                       base_open_reports_date)
    query_base_runs = get_diff_run_id_query(session, run_ids, base_tag_ids)

    query_new = get_diff_bug_id_query(session, cmp_data.runIds,
                                      cmp_data.runTag,
                                      cmp_data.openReportsDate)
    query_new_runs = get_diff_run_id_query(session, cmp_data.runIds,
                                           cmp_data.runTag)

    AND = []
    if cmp_data.diffType == DiffType.NEW:
        return and_(Report.bug_id.in_(query_new.except_(query_base)),
                    Report.run_id.in_(query_new_runs)), [Run]

    elif cmp_data.diffType == DiffType.RESOLVED:
        return and_(Report.bug_id.in_(query_base.except_(query_new)),
                    Report.run_id.in_(query_base_runs)), [Run]

    elif cmp_data.diffType == DiffType.UNRESOLVED:
        return and_(Report.bug_id.in_(query_base.intersect(query_new)),
                    Report.run_id.in_(query_new_runs)), [Run]

    else:
        raise codechecker_api_shared.ttypes.RequestFailed(
            codechecker_api_shared.ttypes.ErrorCode.DATABASE,
            'Unsupported diff type: ' + str(cmp_data.diffType))

    return and_(*AND), []


def process_run_history_filter(query, run_ids, run_history_filter):
    """
    Process run history filter.
    """
    if run_ids:
        query = query.filter(RunHistory.run_id.in_(run_ids))

    if run_history_filter:
        if run_history_filter.tagNames:
            OR = [RunHistory.version_tag.ilike('{0}'.format(conv(
                escape_like(name, '\\'))), escape='\\') for
                name in run_history_filter.tagNames]

            query = query.filter(or_(*OR))

        if run_history_filter.tagIds:
            query = query.filter(RunHistory.id.in_(run_history_filter.tagIds))

        stored = run_history_filter.stored
        if stored:
            if stored.before:
                stored_before = datetime.fromtimestamp(stored.before)
                query = query.filter(RunHistory.time <= stored_before)

            if stored.after:
                stored_after = datetime.fromtimestamp(stored.after)
                query = query.filter(RunHistory.time >= stored_after)

    return query


def process_run_filter(session, query, run_filter):
    """
    Process run filter.
    """
    if run_filter is None:
        return query

    if run_filter.ids:
        query = query.filter(Run.id.in_(run_filter.ids))
    if run_filter.names:
        if run_filter.exactMatch:
            query = query.filter(Run.name.in_(run_filter.names))
        else:
            OR = [Run.name.ilike('{0}'.format(conv(
                escape_like(name, '\\'))), escape='\\') for
                name in run_filter.names]
            query = query.filter(or_(*OR))

    if run_filter.beforeTime:
        date = datetime.fromtimestamp(run_filter.beforeTime)
        query = query.filter(Run.date < date)

    if run_filter.afterTime:
        date = datetime.fromtimestamp(run_filter.afterTime)
        query = query.filter(Run.date > date)

    if run_filter.beforeRun:
        run = session.query(Run.date) \
            .filter(Run.name == run_filter.beforeRun) \
            .one_or_none()

        if run:
            query = query.filter(Run.date < run.date)

    if run_filter.afterRun:
        run = session.query(Run.date) \
            .filter(Run.name == run_filter.afterRun) \
            .one_or_none()

        if run:
            query = query.filter(Run.date > run.date)

    return query


def get_report_details(session, report_ids):
    """
    Returns report details for the given report ids.
    """
    details = {}

    # Get bug path events.
    bug_path_events = session.query(BugPathEvent, File.filepath) \
        .filter(BugPathEvent.report_id.in_(report_ids)) \
        .outerjoin(File,
                   File.id == BugPathEvent.file_id) \
        .order_by(BugPathEvent.report_id, BugPathEvent.order)

    bug_events_list = defaultdict(list)
    for event, file_path in bug_path_events:
        report_id = event.report_id
        event = bugpathevent_db_to_api(event)
        event.filePath = file_path
        bug_events_list[report_id].append(event)

    # Get bug report points.
    bug_report_points = session.query(BugReportPoint, File.filepath) \
        .filter(BugReportPoint.report_id.in_(report_ids)) \
        .outerjoin(File,
                   File.id == BugReportPoint.file_id) \
        .order_by(BugReportPoint.report_id, BugReportPoint.order)

    bug_point_list = defaultdict(list)
    for bug_point, file_path in bug_report_points:
        report_id = bug_point.report_id
        bug_point = bugreportpoint_db_to_api(bug_point)
        bug_point.filePath = file_path
        bug_point_list[report_id].append(bug_point)

    # Get extended report data.
    extended_data_list = defaultdict(list)
    q = session.query(ExtendedReportData, File.filepath) \
        .filter(ExtendedReportData.report_id.in_(report_ids)) \
        .outerjoin(File,
                   File.id == ExtendedReportData.file_id)

    for data, file_path in q:
        report_id = data.report_id
        extended_data = extended_data_db_to_api(data)
        extended_data.filePath = file_path
        extended_data_list[report_id].append(extended_data)

    # Get Comments for report data
    comment_data_list = defaultdict(list)
    comment_query = session.query(Comment, Report.id)\
        .filter(Report.id.in_(report_ids)) \
        .outerjoin(Report, Report.bug_id == Comment.bug_hash) \
        .order_by(Comment.created_at.desc())

    for data, report_id in comment_query:
        report_id = report_id
        comment_data = comment_data_db_to_api(data)
        comment_data_list[report_id].append(comment_data)

    for report_id in report_ids:
        details[report_id] = \
            ReportDetails(pathEvents=bug_events_list[report_id],
                          executionPath=bug_point_list[report_id],
                          extendedData=extended_data_list[report_id],
                          comments=comment_data_list[report_id])

    return details


def bugpathevent_db_to_api(bpe):
    return ttypes.BugPathEvent(
        startLine=bpe.line_begin,
        startCol=bpe.col_begin,
        endLine=bpe.line_end,
        endCol=bpe.col_end,
        msg=bpe.msg,
        fileId=bpe.file_id)


def bugreportpoint_db_to_api(brp):
    return BugPathPos(
        startLine=brp.line_begin,
        startCol=brp.col_begin,
        endLine=brp.line_end,
        endCol=brp.col_end,
        fileId=brp.file_id)


def extended_data_db_to_api(erd):
    return ttypes.ExtendedReportData(
        type=report_extended_data_type_enum(erd.type),
        startLine=erd.line_begin,
        startCol=erd.col_begin,
        endLine=erd.line_end,
        endCol=erd.col_end,
        message=erd.message,
        fileId=erd.file_id)


def comment_data_db_to_api(comm):
    """
    Returns a CommentData Object with all the relevant fields
    """
    return ttypes.CommentData(
        id=comm.id,
        author=comm.author,
        message=get_comment_msg(comm),
        createdAt=str(comm.created_at),
        kind=comm.kind
    )


def get_comment_msg(comment):
    """
    Checks for the comment kind. If the comment is
    identified as a system comment, it is formatted accordindly.
    """
    context = webserver_context.get_context()
    message = comment.message.decode('utf-8')
    sys_comment = comment_kind_from_thrift_type(ttypes.CommentKind.SYSTEM)

    if comment.kind == sys_comment:
        try:
            elements = shlex.split(message)
        except ValueError:
            # In earlier CodeChecker we saved system comments
            # without escaping special characters such as
            # quotes. This is kept only for backward
            # compatibility reason.
            message = message \
                .replace("'", "\\'") \
                .replace('"', '\\"')

            elements = shlex.split(message)

        system_comment = context.system_comment_map.get(elements[0])
        if system_comment:
            for idx, value in enumerate(elements[1:]):
                system_comment = system_comment.replace(
                    '{' + str(idx) + '}', html.escape(value))
            return system_comment

    return html.escape(message)


def create_review_data(
    review_status: str,
    message: Optional[str],
    author,
    date,
    is_in_source: bool
):
    return ReviewData(
        status=review_status_enum(review_status),
        comment=None if message is None else message.decode('utf-8'),
        author=author,
        date=None if date is None else str(date),
        isInSource=is_in_source)


def create_count_expression(report_filter):
    if report_filter is not None and report_filter.isUnique:
        return func.count(Report.bug_id.distinct())
    else:
        return func.count(literal_column('*'))


def apply_report_filter(q, filter_expression, join_tables):
    """
    Applies the given filter expression and joins the File, Run and RunHistory
    tables if necessary based on join_tables parameter.
    """
    if File in join_tables:
        q = q.outerjoin(File, Report.file_id == File.id)
    if Run in join_tables:
        q = q.outerjoin(Run, Run.id == Report.run_id)
    if RunHistory in join_tables:
        q = q.outerjoin(RunHistory, RunHistory.run_id == Report.run_id)

    return q.filter(filter_expression)


def get_sort_map(sort_types, is_unique=False):
    # Get a list of sort_types which will be a nested ORDER BY.
    sort_type_map = {
        SortType.FILENAME: [(File.filepath, 'filepath'),
                            (Report.line, 'line')],
        SortType.BUG_PATH_LENGTH: [(Report.path_length, 'bug_path_length')],
        SortType.CHECKER_NAME: [(Report.checker_id, 'checker_id')],
        SortType.SEVERITY: [(Report.severity, 'severity')],
        SortType.REVIEW_STATUS: [(Report.review_status, 'rw_status')],
        SortType.DETECTION_STATUS: [(Report.detection_status, 'dt_status')]}

    if is_unique:
        sort_type_map[SortType.FILENAME] = [(File.filename, 'filename')]
        sort_type_map[SortType.DETECTION_STATUS] = []

    # Mapping the SQLAlchemy functions.
    order_type_map = {Order.ASC: asc, Order.DESC: desc}

    if sort_types is None:
        sort_types = [SortMode(SortType.SEVERITY, Order.DESC)]

    return sort_types, sort_type_map, order_type_map


def sort_results_query(query, sort_types, sort_type_map, order_type_map,
                       order_by_label=False):
    """
    Helper method for __queryDiffResults and queryResults to apply sorting.
    """
    for sort in sort_types:
        sorttypes = sort_type_map.get(sort.type)
        for sorttype in sorttypes:
            order_type = order_type_map.get(sort.ord)
            sort_col = sorttype[1] if order_by_label else sorttype[0]
            query = query.order_by(order_type(sort_col))

    return query


def filter_unresolved_reports(q):
    """
    Filter reports which are unresolved.

    Note: review status of these reports are not in skip_review_statuses
    and detection statuses are not in skip_detection_statuses.
    """
    skip_review_statuses = ['false_positive', 'intentional']
    skip_detection_statuses = ['resolved', 'off', 'unavailable']

    return q.filter(Report.detection_status.notin_(skip_detection_statuses)) \
            .filter(Report.review_status.notin_(skip_review_statuses))


def check_remove_runs_lock(session, run_ids):
    """
    Check if there is an existing lock on the given runs, which has not
    expired yet. If so, the run cannot be deleted, as someone is assumed to
    be storing into it.
    """
    locks_expired_at = datetime.now() - timedelta(
        seconds=db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE)

    run_locks = session.query(RunLock.name) \
        .filter(RunLock.locked_at >= locks_expired_at)

    if run_ids:
        run_locks = run_locks.filter(Run.id.in_(run_ids))

    run_locks = run_locks \
        .outerjoin(Run,
                   Run.name == RunLock.name) \
        .all()

    if run_locks:
        raise codechecker_api_shared.ttypes.RequestFailed(
            codechecker_api_shared.ttypes.ErrorCode.DATABASE,
            "Can not remove results because the following runs "
            "are locked: {0}".format(
                ', '.join([r[0] for r in run_locks])))


def sort_run_data_query(query, sort_mode):
    """
    Sort run data query by the given sort type.
    """
    # Sort by run date by default.
    if not sort_mode:
        return query.order_by(desc(Run.date))

    order_type_map = {Order.ASC: asc, Order.DESC: desc}
    order_type = order_type_map.get(sort_mode.ord)
    if sort_mode.type == RunSortType.NAME:
        query = query.order_by(order_type(Run.name))
    elif sort_mode.type == RunSortType.UNRESOLVED_REPORTS:
        query = query.order_by(order_type('report_count'))
    elif sort_mode.type == RunSortType.DATE:
        query = query.order_by(order_type(Run.date))
    elif sort_mode.type == RunSortType.DURATION:
        query = query.order_by(order_type(Run.duration))
    elif sort_mode.type == RunSortType.CC_VERSION:
        query = query.order_by(order_type(RunHistory.cc_version))

    return query


def get_failed_files_query(session, run_ids, query_fields,
                           extra_sub_query_fields=None):
    """
    General function to get query to fetch the list of failed files and to get
    the number of failed files.
    """
    sub_query_fields = [func.max(RunHistory.id).label('history_id')]
    if extra_sub_query_fields:
        sub_query_fields.extend(extra_sub_query_fields)

    sub_q = session.query(*sub_query_fields)

    if run_ids:
        sub_q = sub_q.filter(RunHistory.run_id.in_(run_ids))

    sub_q = sub_q \
        .group_by(RunHistory.run_id) \
        .subquery()

    query = session \
        .query(*query_fields) \
        .outerjoin(sub_q,
                   AnalyzerStatistic.run_history_id == sub_q.c.history_id) \
        .filter(AnalyzerStatistic.run_history_id == sub_q.c.history_id)

    return query, sub_q


def get_analysis_statistics_query(session, run_ids, run_history_ids=None):
    """ Get analyzer statistics query. """
    query = session.query(AnalyzerStatistic, Run.id)

    if run_ids:
        # Subquery to get analyzer statistics only for these run history id's.
        history_ids_subq = session.query(
                func.max(AnalyzerStatistic.run_history_id)) \
            .filter(RunHistory.run_id.in_(run_ids)) \
            .outerjoin(
                RunHistory,
                RunHistory.id == AnalyzerStatistic.run_history_id) \
            .group_by(RunHistory.run_id) \
            .subquery()

        query = query.filter(
            AnalyzerStatistic.run_history_id.in_(history_ids_subq))
    elif run_history_ids:
        query = query.filter(RunHistory.id.in_(run_history_ids))

    return query \
        .outerjoin(RunHistory,
                   RunHistory.id == AnalyzerStatistic.run_history_id) \
        .outerjoin(Run,
                   Run.id == RunHistory.run_id)


def get_commit_url(
    remote_url: Optional[str],
    git_commit_urls: List
) -> Optional[str]:
    """ Get commit url for the given remote url. """
    if not remote_url:
        return

    for git_commit_url in git_commit_urls:
        m = git_commit_url["regex"].match(remote_url)
        if m:
            url = git_commit_url["url"]
            for key, value in m.groupdict().items():
                if value is not None:
                    url = url.replace(f"${key}", value)

            return url


def get_cleanup_plan(session, cleanup_plan_id: int) -> CleanupPlan:
    """
    Check if the given cleanup id exists in the database and returns
    the cleanup. Otherwise it will raise an exception.
    """
    cleanup_plan = session.query(CleanupPlan).get(cleanup_plan_id)

    if not cleanup_plan:
        raise codechecker_api_shared.ttypes.RequestFailed(
            codechecker_api_shared.ttypes.ErrorCode.DATABASE,
            f"Cleanup plan '{cleanup_plan_id}' was not found in the database.")

    return cleanup_plan


def get_cleanup_plan_report_hashes(
    session,
    cleanup_plan_ids: List[int]
) -> Dict[int, List[str]]:
    """ Get report hashes for the given cleanup plan ids. """
    cleanup_plan_hashes = defaultdict(list)

    q = session \
        .query(
            CleanupPlanReportHash.cleanup_plan_id,
            CleanupPlanReportHash.bug_hash) \
        .filter(CleanupPlanReportHash.cleanup_plan_id.in_(
            cleanup_plan_ids))

    for cleanup_plan_id, report_hash in q:
        cleanup_plan_hashes[cleanup_plan_id].append(report_hash)

    return cleanup_plan_hashes


def sort_review_statuses_query(
    query,
    sort_mode: ReviewStatusRuleSortMode,
    report_count_label
):
    """
    Sort review status rule query by the given sort mode.
    """
    # Sort by rule date by default.
    if not sort_mode:
        return query.order_by(desc(ReviewStatus.date))

    order_type_map = {Order.ASC: asc, Order.DESC: desc}
    order_type = order_type_map.get(sort_mode.ord)
    if sort_mode.type == ReviewStatusRuleSortType.REPORT_HASH:
        query = query.order_by(order_type(ReviewStatus.bug_hash))
    elif sort_mode.type == ReviewStatusRuleSortType.STATUS:
        query = query.order_by(order_type(ReviewStatus.status))
    elif sort_mode.type == ReviewStatusRuleSortType.AUTHOR:
        query = query.order_by(order_type(ReviewStatus.author))
    elif sort_mode.type == ReviewStatusRuleSortType.DATE:
        query = query.order_by(order_type(ReviewStatus.date))
    elif sort_mode.type == ReviewStatusRuleSortType.ASSOCIATED_REPORTS_COUNT:
        query = query.order_by(order_type(report_count_label))

    return query


def process_rs_rule_filter(
    query,
    rule_filter: Optional[ReviewStatusRuleFilter] = None
):
    """ Process review status rule filter. """
    if rule_filter:
        if rule_filter.reportHashes is not None:
            OR = [ReviewStatus.bug_hash.ilike(conv(report_hash))
                  for report_hash in rule_filter.reportHashes]
            query = query.filter(or_(*OR))

        if rule_filter.reviewStatuses is not None:
            query = query.filter(
                ReviewStatus.status.in_(
                    map(review_status_str, rule_filter.reviewStatuses)))

        if rule_filter.authors is not None:
            OR = [ReviewStatus.author.ilike(conv(author))
                  for author in rule_filter.authors]
            query = query.filter(or_(*OR))

    return query


def get_rs_rule_query(
    session: DBSession,
    rule_filter: Optional[ReviewStatusRuleFilter] = None,
    sort_mode: Optional[ReviewStatusRuleSortMode] = None
):
    """ Returns query to get review status rules. """
    report_count = func.count(Report.id).label('report_count')
    q = session \
        .query(ReviewStatus, report_count) \
        .join(Report,
              Report.bug_id == ReviewStatus.bug_hash,
              isouter=True)
    q = process_rs_rule_filter(q, rule_filter)

    if sort_mode:
        q = sort_review_statuses_query(q, sort_mode, report_count)

    q = q.group_by(ReviewStatus.bug_hash)

    # Filter review status rules by aggregate columns.
    if rule_filter and rule_filter.noAssociatedReports:
        q = q.having(report_count == 0)

    return q


class ThriftRequestHandler:
    """
    Connect to database and handle thrift client requests.
    """

    def __init__(self,
                 manager,
                 Session,
                 product,
                 auth_session,
                 config_database,
                 package_version,
                 context):

        if not product:
            raise ValueError("Cannot initialize request handler without "
                             "a product to serve.")

        self._manager = manager
        self._product = product
        self._auth_session = auth_session
        self._config_database = config_database
        self.__package_version = package_version
        self._Session = Session
        self._context = context
        self.__permission_args = {
            'productID': product.id
        }

    def _get_username(self):
        """
        Returns the actually logged in user name.
        """
        return self._auth_session.user if self._auth_session else "Anonymous"

    def _set_run_data_for_curr_product(
        self,
        inc_num_of_runs: Optional[int],
        latest_storage_date: Optional[datetime] = None
    ):
        """
        Increment the number of runs related to the current product with the
        given value and set the latest storage date.
        """
        values = {}

        if inc_num_of_runs is not None:
            values["num_of_runs"] = Product.num_of_runs + inc_num_of_runs

        if latest_storage_date is not None:
            values["latest_storage_date"] = latest_storage_date

        with DBSession(self._config_database) as session:
            session.query(Product) \
                .filter(Product.id == self._product.id) \
                .update(values)

            session.commit()

    def __require_permission(self, required):
        """
        Helper method to raise an UNAUTHORIZED exception if the user does not
        have any of the given permissions.
        """

        with DBSession(self._config_database) as session:
            args = dict(self.__permission_args)
            args['config_db_session'] = session

            if not any([permissions.require_permission(
                    perm, args, self._auth_session)
                    for perm in required]):
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You are not authorized to execute this action.")

            return True

    def __require_admin(self):
        self.__require_permission([permissions.PRODUCT_ADMIN])

    def __require_access(self):
        self.__require_permission([permissions.PRODUCT_ACCESS])

    def __require_store(self):
        self.__require_permission([permissions.PRODUCT_STORE])

    def __require_view(self):
        self.__require_permission([permissions.PRODUCT_VIEW])

    def __add_comment(self, bug_id, message, kind=CommentKindValue.USER,
                      date=None):
        """ Creates a new comment object. """
        user = self._get_username()
        return Comment(bug_id,
                       user,
                       message.encode('utf-8'),
                       kind,
                       date or datetime.now())

    @timeit
    def getRunData(self, run_filter, limit, offset, sort_mode):
        self.__require_view()

        limit = verify_limit_range(limit)

        with DBSession(self._Session) as session:

            # Count the reports subquery.
            stmt = session.query(Report.run_id,
                                 func.count(Report.bug_id)
                                 .label('report_count'))

            stmt = filter_unresolved_reports(stmt) \
                .group_by(Report.run_id).subquery()

            tag_q = session.query(RunHistory.run_id,
                                  func.max(RunHistory.id).label(
                                      'run_history_id'),
                                  func.max(RunHistory.time).label(
                                      'run_history_time')) \
                .group_by(RunHistory.run_id) \
                .subquery()

            q = session.query(Run.id,
                              Run.date,
                              Run.name,
                              Run.duration,
                              RunHistory.version_tag,
                              RunHistory.cc_version,
                              RunHistory.description,
                              stmt.c.report_count)

            q = process_run_filter(session, q, run_filter)

            q = q.outerjoin(stmt, Run.id == stmt.c.run_id) \
                .outerjoin(tag_q, Run.id == tag_q.c.run_id) \
                .outerjoin(RunHistory,
                           RunHistory.id == tag_q.c.run_history_id) \
                .group_by(Run.id,
                          RunHistory.version_tag,
                          RunHistory.cc_version,
                          RunHistory.description,
                          stmt.c.report_count)

            q = sort_run_data_query(q, sort_mode)

            if limit:
                q = q.limit(limit).offset(offset)

            # Get the runs.
            run_data = q.all()

            # Set run ids filter by using the previous results.
            if not run_filter:
                run_filter = RunFilter()

            run_filter.ids = [r[0] for r in run_data]

            # Get report count for each detection statuses.
            status_q = session.query(Report.run_id,
                                     Report.detection_status,
                                     func.count(Report.bug_id)) \
                .filter(Report.run_id.in_(run_filter.ids)) \
                .group_by(Report.run_id, Report.detection_status)

            status_sum = defaultdict(defaultdict)
            for run_id, status, count in status_q:
                status_sum[run_id][detection_status_enum(status)] = count

            # Get analyzer statistics.
            analyzer_statistics = defaultdict(lambda: defaultdict())

            stat_q = get_analysis_statistics_query(session, run_filter.ids)
            for stat, run_id in stat_q:
                analyzer_statistics[run_id][stat.analyzer_type] = \
                    ttypes.AnalyzerStatistics(failed=stat.failed,
                                              successful=stat.successful)

            results = []

            for run_id, run_date, run_name, duration, tag, cc_version, \
                description, report_count \
                    in run_data:

                if report_count is None:
                    report_count = 0

                analyzer_stats = analyzer_statistics[run_id]
                results.append(RunData(runId=run_id,
                                       runDate=str(run_date),
                                       name=run_name,
                                       duration=duration,
                                       resultCount=report_count,
                                       detectionStatusCount=status_sum[run_id],
                                       versionTag=tag,
                                       codeCheckerVersion=cc_version,
                                       analyzerStatistics=analyzer_stats,
                                       description=description))
            return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunCount(self, run_filter):
        self.__require_view()

        with DBSession(self._Session) as session:
            query = session.query(Run.id)
            query = process_run_filter(session, query, run_filter)

        return query.count()

    # DEPRECATED: use getAnalysisInfo API function instead of this function.
    def getCheckCommand(self, run_history_id, run_id):
        """ Get analyzer command based on the given filter. """
        self.__require_view()

        limit = None
        offset = 0
        analysis_info_filter = AnalysisInfoFilter(
            runId=run_id,
            runHistoryId=run_history_id)

        analysis_info = self.getAnalysisInfo(
            analysis_info_filter, limit, offset)

        return "; ".join([html.escape(i.analyzerCommand)
                          for i in analysis_info])

    @exc_to_thrift_reqfail
    @timeit
    def getAnalysisInfo(self, analysis_info_filter, limit, offset):
        """ Get analysis information based on the given filter. """
        self.__require_view()

        res: List[ttypes.AnalysisInfo] = []
        if not analysis_info_filter:
            return res

        analysis_info_query = None
        with DBSession(self._Session) as session:
            run_id = analysis_info_filter.runId
            run_history_ids = None
            if run_id is not None:
                run_history_ids = session \
                    .query(RunHistory.id) \
                    .filter(RunHistory.run_id == run_id) \
                    .order_by(RunHistory.time.desc()) \
                    .limit(1)

            if run_history_ids is None:
                run_history_ids = [analysis_info_filter.runHistoryId]

            if run_history_ids is not None:
                rh_a_tbl = RunHistoryAnalysisInfo
                analysis_info_query = session.query(AnalysisInfo) \
                    .outerjoin(
                        rh_a_tbl,
                        rh_a_tbl.c.analysis_info_id == AnalysisInfo.id) \
                    .filter(rh_a_tbl.c.run_history_id.in_(run_history_ids))

            report_id = analysis_info_filter.reportId
            if report_id is not None:
                r_a_tbl = ReportAnalysisInfo
                analysis_info_query = session.query(AnalysisInfo) \
                    .outerjoin(
                        r_a_tbl,
                        r_a_tbl.c.analysis_info_id == AnalysisInfo.id) \
                    .filter(r_a_tbl.c.report_id == report_id)

            if analysis_info_query:
                if limit:
                    analysis_info_query = analysis_info_query \
                        .limit(limit).offset(offset)

                for cmd in analysis_info_query:
                    command = \
                        zlib.decompress(cmd.analyzer_command).decode('utf-8')

                    res.append(ttypes.AnalysisInfo(
                        analyzerCommand=html.escape(command)))

        return res

    @exc_to_thrift_reqfail
    @timeit
    def getRunHistory(self, run_ids, limit, offset, run_history_filter):
        self.__require_view()

        limit = verify_limit_range(limit)

        with DBSession(self._Session) as session:

            res = session.query(RunHistory)

            res = process_run_history_filter(res, run_ids, run_history_filter)

            res = res.order_by(RunHistory.time.desc())

            if limit:
                res = res.limit(limit).offset(offset)

            results = []
            for history in res:
                analyzer_statistics = {}
                for stat in history.analyzer_statistics:
                    analyzer_statistics[stat.analyzer_type] = \
                        ttypes.AnalyzerStatistics(
                            failed=stat.failed,
                            successful=stat.successful)

                results.append(RunHistoryData(
                    id=history.id,
                    runId=history.run.id,
                    runName=history.run.name,
                    versionTag=history.version_tag,
                    user=history.user,
                    time=str(history.time),
                    codeCheckerVersion=history.cc_version,
                    analyzerStatistics=analyzer_statistics,
                    description=history.description))

            return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunHistoryCount(self, run_ids, run_history_filter):
        self.__require_view()

        with DBSession(self._Session) as session:
            query = session.query(RunHistory.id)
            query = process_run_history_filter(query,
                                               run_ids,
                                               run_history_filter)

        return query.count()

    @exc_to_thrift_reqfail
    @timeit
    def getReport(self, reportId):
        self.__require_view()

        with DBSession(self._Session) as session:

            result = session \
                .query(Report, File) \
                .filter(Report.id == reportId) \
                .outerjoin(File, Report.file_id == File.id) \
                .limit(1).one_or_none()

            if not result:
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    "Report " + str(reportId) + " not found!")

            report, source_file = result
            return ReportData(
                runId=report.run_id,
                bugHash=report.bug_id,
                checkedFile=source_file.filepath,
                checkerMsg=report.checker_message,
                reportId=report.id,
                fileId=source_file.id,
                line=report.line,
                column=report.column,
                checkerId=report.checker_id,
                severity=report.severity,
                reviewData=create_review_data(
                    report.review_status,
                    report.review_status_message,
                    report.review_status_author,
                    report.review_status_date,
                    report.review_status_is_in_source),
                detectionStatus=detection_status_enum(report.detection_status),
                detectedAt=str(report.detected_at),
                fixedAt=str(report.fixed_at) if report.fixed_at else None)

    @exc_to_thrift_reqfail
    @timeit
    def getDiffResultsHash(self, run_ids, report_hashes, diff_type,
                           skip_detection_statuses, tag_ids):
        self.__require_view()

        if not skip_detection_statuses:
            skip_detection_statuses = [ttypes.DetectionStatus.RESOLVED,
                                       ttypes.DetectionStatus.OFF,
                                       ttypes.DetectionStatus.UNAVAILABLE]

        # Convert statuses to string.
        skip_statuses_str = [detection_status_str(status)
                             for status in skip_detection_statuses]

        with DBSession(self._Session) as session:
            if diff_type == DiffType.NEW:
                # In postgresql we can select multiple rows filled with
                # constants by using `unnest` function. In sqlite we have to
                # use multiple UNION ALL.

                if not report_hashes:
                    return []

                base_hashes = session.query(Report.bug_id.label('bug_id')) \
                    .outerjoin(File, Report.file_id == File.id) \
                    .filter(
                        Report.detection_status.notin_(skip_statuses_str),
                        Report.fixed_at.is_(None))

                base_hashes = \
                    filter_open_reports_in_tags(base_hashes, run_ids, tag_ids)

                if self._product.driver_name == 'postgresql':
                    new_hashes = select([func.unnest(report_hashes)
                                         .label('bug_id')]) \
                        .except_(base_hashes).alias('new_bugs')
                    return [res[0] for res in session.query(new_hashes)]
                else:
                    # The maximum number of compound select in sqlite is 500
                    # by default. We increased SQLITE_MAX_COMPOUND_SELECT
                    # limit but when the number of compound select was larger
                    # than 8435 sqlite threw a `Segmentation fault` error.
                    # For this reason we create queries with chunks.
                    new_hashes = []
                    for chunk in util.chunks(iter(report_hashes),
                                             SQLITE_MAX_COMPOUND_SELECT):
                        new_hashes_query = union_all(*[
                            select([bindparam('bug_id' + str(i), h)
                                    .label('bug_id')])
                            for i, h in enumerate(chunk)])
                        q = select([new_hashes_query]).except_(base_hashes)
                        new_hashes.extend([res[0] for res in session.query(q)])

                    return new_hashes
            elif diff_type == DiffType.RESOLVED:
                results = session.query(Report.bug_id) \
                    .filter(or_(Report.bug_id.notin_(report_hashes),
                                Report.fixed_at.isnot(None)))

                results = \
                    filter_open_reports_in_tags(results, run_ids, tag_ids)

                return [res[0] for res in results]

            elif diff_type == DiffType.UNRESOLVED:
                results = session.query(Report.bug_id) \
                    .filter(Report.bug_id.in_(report_hashes)) \
                    .filter(Report.detection_status.notin_(
                        skip_statuses_str)) \
                    .filter(Report.fixed_at.is_(None))

                results = \
                    filter_open_reports_in_tags(results, run_ids, tag_ids)

                return [res[0] for res in results]

            else:
                return []

    @exc_to_thrift_reqfail
    @timeit
    def getRunResults(self, run_ids, limit, offset, sort_types,
                      report_filter, cmp_data, get_details):
        self.__require_view()

        limit = verify_limit_range(limit)

        with DBSession(self._Session) as session:
            results = []

            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                sort_types, sort_type_map, order_type_map = \
                    get_sort_map(sort_types, True)

                selects = [func.max(Report.id).label('id')]
                for sort in sort_types:
                    sorttypes = sort_type_map.get(sort.type)
                    for sorttype in sorttypes:
                        if sorttype[0] != 'bug_path_length':
                            selects.append(func.max(sorttype[0])
                                           .label(sorttype[1]))

                unique_reports = session.query(*selects)
                unique_reports = apply_report_filter(unique_reports,
                                                     filter_expression,
                                                     join_tables)
                unique_reports = unique_reports \
                    .group_by(Report.bug_id) \
                    .subquery()

                # Sort the results
                sorted_reports = \
                    session.query(unique_reports.c.id)

                sorted_reports = sort_results_query(sorted_reports,
                                                    sort_types,
                                                    sort_type_map,
                                                    order_type_map,
                                                    True)

                sorted_reports = sorted_reports \
                    .limit(limit).offset(offset).subquery()

                q = session.query(Report.id, Report.bug_id,
                                  Report.checker_message, Report.checker_id,
                                  Report.severity, Report.detected_at,
                                  Report.fixed_at, Report.review_status,
                                  Report.review_status_author,
                                  Report.review_status_message,
                                  Report.review_status_date,
                                  Report.review_status_is_in_source,
                                  File.filename, File.filepath,
                                  Report.path_length, Report.analyzer_name) \
                    .outerjoin(File, Report.file_id == File.id) \
                    .outerjoin(sorted_reports,
                               sorted_reports.c.id == Report.id) \
                    .filter(sorted_reports.c.id.isnot(None))

                # We have to sort the results again because an ORDER BY in a
                # subtable is broken by the JOIN.
                q = sort_results_query(q,
                                       sort_types,
                                       sort_type_map,
                                       order_type_map)

                query_result = q.all()

                # Get report details if it is required.
                report_details = {}
                if get_details:
                    report_ids = [r[0] for r in query_result]
                    report_details = get_report_details(session, report_ids)

                for report_id, bug_id, checker_msg, checker, severity, \
                    detected_at, fixed_at, review_status, \
                    review_status_author, review_status_message, \
                    review_status_date, review_status_is_in_source, \
                    filename, _, bug_path_len, \
                        analyzer_name in query_result:

                    review_data = create_review_data(
                        review_status,
                        review_status_message,
                        review_status_author,
                        review_status_date,
                        review_status_is_in_source)

                    results.append(
                        ReportData(bugHash=bug_id,
                                   checkedFile=filename,
                                   checkerMsg=checker_msg,
                                   checkerId=checker,
                                   severity=severity,
                                   reviewData=review_data,
                                   detectedAt=str(detected_at),
                                   fixedAt=str(fixed_at),
                                   bugPathLength=bug_path_len,
                                   details=report_details.get(report_id),
                                   analyzerName=analyzer_name))
            else:
                sort_types, sort_type_map, order_type_map = \
                    get_sort_map(sort_types)

                if SortType.FILENAME in map(lambda x: x.type, sort_types):
                    join_tables.append(File)

                q = session.query(Report.run_id, Report.id, Report.file_id,
                                  Report.line, Report.column,
                                  Report.detection_status, Report.bug_id,
                                  Report.checker_message, Report.checker_id,
                                  Report.severity, Report.detected_at,
                                  Report.fixed_at, Report.review_status,
                                  Report.review_status_author,
                                  Report.review_status_message,
                                  Report.review_status_date,
                                  Report.review_status_is_in_source,
                                  Report.path_length, Report.analyzer_name)
                q = apply_report_filter(q, filter_expression, join_tables)

                q = sort_results_query(q, sort_types, sort_type_map,
                                       order_type_map)

                q = q.limit(limit).offset(offset)

                query_result = q.all()

                # Get report details if it is required.
                report_details = {}
                if get_details:
                    report_ids = [r[1] for r in query_result]
                    report_details = get_report_details(session, report_ids)

                # Earlier file table was joined to the query of reports.
                # However, that created an SQL strategy in PostgreSQL which
                # resulted in timeout. Based on heuristics the query strategy
                # (which not only depends on the query statement but the table
                # size and many other things) may contain an inner loop on
                # "reports" table which is one of the largest tables. This
                # separate query of file table results a query strategy for the
                # previous query which doesn't contain such an inner loop. See
                # EXPLAIN SELECT columns FROM ...
                file_ids = set(map(lambda r: r[2], query_result))
                all_files = dict()
                for chunk in util.chunks(file_ids, SQLITE_MAX_VARIABLE_NUMBER):
                    all_files.update(dict(session.query(File.id, File.filepath)
                                     .filter(File.id.in_(chunk)).all()))

                for run_id, report_id, file_id, line, column, d_status, \
                    bug_id, checker_msg, checker, severity, detected_at,\
                    fixed_at, review_status, review_status_author, \
                    review_status_message, review_status_date, \
                    review_status_is_in_source, bug_path_len, \
                        analyzer_name in query_result:

                    review_data = create_review_data(
                        review_status,
                        review_status_message,
                        review_status_author,
                        review_status_date,
                        review_status_is_in_source)

                    results.append(
                        ReportData(runId=run_id,
                                   bugHash=bug_id,
                                   checkedFile=all_files[file_id],
                                   checkerMsg=checker_msg,
                                   reportId=report_id,
                                   fileId=file_id,
                                   line=line,
                                   column=column,
                                   checkerId=checker,
                                   severity=severity,
                                   reviewData=review_data,
                                   detectionStatus=detection_status_enum(
                                       d_status),
                                   detectedAt=str(detected_at),
                                   fixedAt=str(fixed_at) if fixed_at else None,
                                   bugPathLength=bug_path_len,
                                   details=report_details.get(report_id),
                                   analyzerName=analyzer_name))

            return results

    @timeit
    def getRunReportCounts(self, run_ids, report_filter, limit, offset):
        """
          Count the results separately for multiple runs.
          If an empty run id list is provided the report
          counts will be calculated for all of the available runs.
        """
        self.__require_view()

        limit = verify_limit_range(limit)

        results = []

        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter)

            count_expr = create_count_expression(report_filter)
            q = session.query(Run.id,
                              Run.name,
                              count_expr) \
                .select_from(Report)

            q = apply_report_filter(
                q, filter_expression, join_tables + [Run])
            q = q.order_by(Run.name).group_by(Run.id)

            if limit:
                q = q.limit(limit).offset(offset)

            for run_id, run_name, count in q:
                report_count = RunReportCount(runId=run_id,
                                              name=run_name,
                                              reportCount=count)
                results.append(report_count)

            return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunResultCount(self, run_ids, report_filter, cmp_data):
        self.__require_view()

        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            q = session.query(Report.bug_id)
            q = apply_report_filter(q, filter_expression, join_tables)

            if report_filter is not None and report_filter.isUnique:
                q = q.group_by(Report.bug_id)

            report_count = q.count()
            if report_count is None:
                report_count = 0

            return report_count

    @exc_to_thrift_reqfail
    @timeit
    def getReportDetails(self, reportId):
        """
        Parameters:
         - reportId
        """
        self.__require_view()
        with DBSession(self._Session) as session:
            return get_report_details(session, [reportId])[reportId]

    def _setReviewStatus(self, session, report_hash, status,
                         message, date=None):
        """
        This function sets the review status of all the reports of a
        given hash. This is the implementation of addReviewStatusRule(),
        but it is also extended with a session parameter which represents a
        database transaction. This is needed because during storage a specific
        session object has to be used.
        """
        review_status = session.query(ReviewStatus).get(report_hash)
        if review_status is None:
            review_status = ReviewStatus()
            review_status.bug_hash = report_hash

        old_status = review_status.status or \
            review_status_str(ttypes.ReviewStatus.UNREVIEWED)
        old_msg = review_status.message or None

        new_status = review_status_str(status)
        new_user = self._get_username()
        new_message = message.encode('utf8') if message else b''

        # Review status is a shared table among runs. When multiple runs
        # are stored in parallel, there may be a race condition in updating
        # review status fields. The most common reason of deadlocks is
        # changing only the date to current date. This condition checks if
        # something else is also changed other than dates.
        # We assume that report status in source code comments belong to
        # the first user who stored the reports. If another user stores the
        # same project with same report status then we don't change it.
        if (old_status, old_msg) == (new_status, new_message):
            return None

        review_status.status = new_status
        review_status.author = new_user
        review_status.message = new_message
        review_status.date = date or datetime.now()
        session.add(review_status)

        # Create a system comment if the review status or the message
        # is changed.
        old_review_status = old_status.capitalize()
        new_review_status = review_status.status.capitalize()
        if message:
            system_comment_msg = \
                'rev_st_changed_msg {0} {1} {2}'.format(
                    old_review_status, new_review_status,
                    shlex.quote(message))
        else:
            system_comment_msg = 'rev_st_changed {0} {1}'.format(
                old_review_status, new_review_status)

        system_comment = self.__add_comment(review_status.bug_hash,
                                            system_comment_msg,
                                            CommentKindValue.SYSTEM,
                                            review_status.date)
        session.add(system_comment)

        # False positive and intentional reports are considered closed, so
        # their "fix date" is set. The reports are reopened when they become
        # unreviewed or confirmed again. Don't change "fix date" for closed
        # report which remain closed.
        if review_status.status in ["false_positive", "intentional"]:
            session \
                .query(Report) \
                .filter(Report.bug_id == report_hash) \
                .filter(Report.detection_status.in_([
                    "unresolved", "new", "reopened"])) \
                .filter(Report.review_status.notin_(
                    ["false_positive", "intentional"])) \
                .filter(Report.review_status_is_in_source.is_(False)) \
                .update(
                    {"fixed_at": review_status.date},
                    synchronize_session=False)
        else:
            reports = session \
                .query(Report) \
                .filter(
                    Report.bug_id == report_hash,
                    Report.detection_status.in_([
                        "unresolved", "new", "reopened"]),
                    Report.review_status.in_([
                        "false_positive", "intentional"]))

            session \
                .query(Report) \
                .filter(Report.id.in_(
                    map(lambda report: report.id, reports))) \
                .filter(Report.review_status_is_in_source.is_(False)) \
                .update({"fixed_at": None}, synchronize_session=False)

        session \
            .query(Report) \
            .filter(Report.review_status_is_in_source.is_(False)) \
            .filter(Report.bug_id == report_hash) \
            .update({
                'review_status': review_status.status,
                'review_status_author': review_status.author,
                'review_status_message': review_status.message,
                'review_status_date': review_status.date})

        session.flush()

        return None

    @exc_to_thrift_reqfail
    @timeit
    def isReviewStatusChangeDisabled(self):
        """
        Return True if review status change is disabled.
        """
        with DBSession(self._config_database) as session:
            product = session.query(Product).get(self._product.id)
            return product.is_review_status_change_disabled

    @exc_to_thrift_reqfail
    @timeit
    def changeReviewStatus(self, report_id, status, message):
        """
        Change the review status of a report by report id.
        """
        self.__require_permission([permissions.PRODUCT_ACCESS,
                                   permissions.PRODUCT_STORE])

        with DBSession(self._Session) as session:
            report = session.query(Report).get(report_id)
            if report:
                # False positive and intentional reports are considered closed,
                # so their "fix date" is set. The reports are reopened when
                # they become unreviewed or confirmed again.
                # Don't change "fix date" for closed
                # report which remain closed.
                if status in ["false_positive", "intentional"]:
                    if report.detection_status in [
                            "unresolved", "new", "reopened"]\
                        and report.review_status not in [
                            "false_positive", "intentional"]:
                        session.query(Report).filter(
                            Report.id == report_id).update(
                                {"fixed_at": datetime.now()})
                elif report.detection_status in [
                    "unresolved", "new", "reopened"]\
                    and report.review_status in [
                        "false_positive", "intentional"]:
                    session.query(Report).filter(
                        Report.id == report_id).update({"fixed_at": None})

                session.query(Report).filter(Report.id == report_id).update({
                        'review_status': review_status_str(status),
                        'review_status_author': self._get_username(),
                        'review_status_message': bytes(message, 'utf-8'),
                        'review_status_date': datetime.now()
                        })
            else:
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    "No report found in the database.")
            session.commit()

            LOG.info("Review status of report '%s' was changed to '%s' by %s.",
                     report_id, review_status_str(status),
                     self._get_username())

        return True

    @exc_to_thrift_reqfail
    @timeit
    def getReviewStatusRules(self, rule_filter, sort_mode, limit, offset):
        self.__require_view()

        result = []
        with DBSession(self._Session) as session:
            if not sort_mode:
                sort_mode = ReviewStatusRuleSortMode(
                    type=ReviewStatusRuleSortType.DATE,
                    ord=Order.DESC)

            q = get_rs_rule_query(session, rule_filter, sort_mode)

            if limit:
                q = q.limit(limit).offset(offset)

        for review_status, associated_report_count in q:
            result.append(ReviewStatusRule(
                reportHash=review_status.bug_hash,
                reviewData=create_review_data(
                    review_status.status,
                    review_status.message,
                    review_status.author,
                    review_status.date,
                    False),
                associatedReportCount=associated_report_count))

        return result

    @exc_to_thrift_reqfail
    @timeit
    def getReviewStatusRulesCount(self, rule_filter):
        self.__require_view()

        with DBSession(self._Session) as session:
            q = get_rs_rule_query(session, rule_filter)
            return q.count()

    @exc_to_thrift_reqfail
    @timeit
    def removeReviewStatusRules(self, rule_filter):
        self.__require_admin()

        with DBSession(self._Session) as session:
            q = get_rs_rule_query(session, rule_filter)
            for review_status, _ in q:
                session.delete(review_status)

                # Reports become unreviewed when the corresponding review
                # status rule is removed and the report doesn't have a review
                # status as source code comment.
                session \
                    .query(Report) \
                    .filter(Report.bug_id == review_status.bug_hash) \
                    .filter(Report.review_status_is_in_source.is_(False)) \
                    .update({
                        'review_status': 'unreviewed',
                        'review_status_author': None,
                        'review_status_message': None,
                        'review_status_date': None,
                        'fixed_at': None})

            session.commit()

            LOG.info("Review status rules were removed based on filter '%s' by"
                     "'%s'.", rule_filter, self._get_username())

            return True

    @exc_to_thrift_reqfail
    @timeit
    def addReviewStatusRule(self, report_hash, review_status, message):
        self.__require_permission([permissions.PRODUCT_ACCESS,
                                   permissions.PRODUCT_STORE])

        if self.isReviewStatusChangeDisabled():
            msg = "Review status change is disabled!"
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL, msg)

        with DBSession(self._Session) as session:
            self._setReviewStatus(
                session, report_hash, review_status, message)
            session.commit()
            return True

    @exc_to_thrift_reqfail
    @timeit
    def getComments(self, report_id):
        """
            Return the list of comments for the given bug.
        """
        self.__require_view()

        with DBSession(self._Session) as session:
            report = session.query(Report).get(report_id)
            if report:
                result = []

                comments = session.query(Comment) \
                    .filter(Comment.bug_hash == report.bug_id) \
                    .order_by(Comment.created_at.desc()) \
                    .all()

                for comment in comments:
                    message = get_comment_msg(comment)
                    result.append(CommentData(
                        comment.id,
                        comment.author,
                        message,
                        str(comment.created_at),
                        comment_kind_to_thrift_type(comment.kind)))

                return result
            else:
                msg = 'Report id ' + str(report_id) + \
                      ' was not found in the database.'
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def getCommentCount(self, report_id):
        """
            Return the number of comments for the given bug.
        """
        self.__require_view()
        with DBSession(self._Session) as session:
            report = session.query(Report).get(report_id)
            if report:
                commentCount = session.query(Comment) \
                    .filter(Comment.bug_hash == report.bug_id) \
                    .count()

            if commentCount is None:
                commentCount = 0

            return commentCount

    @exc_to_thrift_reqfail
    @timeit
    def addComment(self, report_id, comment_data):
        """ Add new comment for the given bug. """
        self.__require_access()

        if not comment_data.message or not comment_data.message.strip():
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                'The comment message can not be empty!')

        with DBSession(self._Session) as session:
            report = session.query(Report).get(report_id)
            if report:
                comment = self.__add_comment(report.bug_id,
                                             comment_data.message)
                session.add(comment)
                session.commit()

                return True
            else:
                msg = 'Report id ' + str(report_id) + \
                      ' was not found in the database.'
                LOG.error(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def updateComment(self, comment_id, content):
        """
            Update the given comment message with new content. We allow
            comments to be updated by it's original author only, except for
            Anyonymous comments that can be updated by anybody.
        """
        self.__require_access()

        if not content.strip():
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                'The comment message can not be empty!')

        with DBSession(self._Session) as session:

            user = self._get_username()

            comment = session.query(Comment).get(comment_id)
            if comment:
                if comment.author != 'Anonymous' and comment.author != user:
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                        'Unathorized comment modification!')

                # Create system comment if the message is changed.
                message = comment.message.decode('utf-8')
                if message != content:
                    system_comment_msg = 'comment_changed {0} {1}'.format(
                        shlex.quote(message),
                        shlex.quote(content))

                    system_comment = \
                        self.__add_comment(comment.bug_hash,
                                           system_comment_msg,
                                           CommentKindValue.SYSTEM)
                    session.add(system_comment)

                comment.message = content.encode('utf-8')
                session.add(comment)

                session.commit()
                return True
            else:
                msg = 'Comment id ' + str(comment_id) + \
                      ' was not found in the database.'
                LOG.error(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def removeComment(self, comment_id):
        """
            Remove the comment. We allow comments to be removed by it's
            original author only, except for Anyonymous comments that can be
            updated by anybody.
        """
        self.__require_access()

        user = self._get_username()

        with DBSession(self._Session) as session:

            comment = session.query(Comment).get(comment_id)
            if comment:
                if comment.author != 'Anonymous' and comment.author != user:
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                        'Unathorized comment modification!')
                session.delete(comment)
                session.commit()

                LOG.info("Comment '%s...' was removed from bug hash '%s' by "
                         "'%s'.", comment.message[:10], comment.bug_hash,
                         self._get_username())

                return True
            else:
                msg = 'Comment id ' + str(comment_id) + \
                      ' was not found in the database.'
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerDoc(self, checkerId):
        """
        Parameters:
         - checkerId
        """

        return ""

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerLabels(
        self,
        checkers: List[ttypes.Checker]
    ) -> List[List[str]]:
        """ Return the list of labels to each checker. """
        labels = []
        for checker in checkers:
            # Analyzer default value in the database is 'unknown' which is not
            # a valid analyzer name. So this code handles this use case.
            analyzer_name = None
            if checker.analyzerName != "unknown":
                analyzer_name = checker.analyzerName

            labels.append(list(map(
                lambda x: f'{x[0]}:{x[1]}',
                self._context.checker_labels.labels_of_checker(
                    checker.checkerId, analyzer_name))))

        return labels

    @exc_to_thrift_reqfail
    @timeit
    def getSourceFileData(self, fileId, fileContent, encoding):
        """
        Parameters:
         - fileId
         - fileContent
         - enum Encoding
        """
        self.__require_view()
        with DBSession(self._Session) as session:
            sourcefile = session.query(File).get(fileId)

            if sourcefile is None:
                return SourceFileData()

            content_hash = sourcefile.content_hash
            cont = session \
                .query(FileContent.content, FileContent.blame_info) \
                .filter(FileContent.content_hash == content_hash) \
                .one_or_none()

            source_file_data = SourceFileData(
                fileId=sourcefile.id,
                filePath=sourcefile.filepath,
                hasBlameInfo=bool(cont.blame_info),
                remoteUrl=get_commit_url(sourcefile.remote_url,
                                         self._context.git_commit_urls),
                trackingBranch=sourcefile.tracking_branch)

            if fileContent:
                source = zlib.decompress(cont.content)

                if encoding == Encoding.BASE64:
                    source = base64.b64encode(source)

                source_file_data.fileContent = source.decode(
                    'utf-8', errors='ignore')

            return source_file_data

    @exc_to_thrift_reqfail
    @timeit
    def getBlameInfo(self, fileId):
        """ Get blame information for the given file. """
        self.__require_view()

        with DBSession(self._Session) as session:
            sourcefile = session.query(File).get(fileId)

            if sourcefile is None:
                return BlameInfo()

            cont = session \
                .query(FileContent.blame_info) \
                .filter(FileContent.content_hash == sourcefile.content_hash) \
                .one_or_none()

            if not cont or not cont.blame_info:
                return BlameInfo()

            try:
                blame_info = json.loads(
                    zlib.decompress(cont.blame_info).decode(
                        'utf-8', errors='ignore'))

                commits = {
                    commitHash: Commit(
                        author=CommitAuthor(
                            name=commit["author"]["name"],
                            email=commit["author"]["email"]),
                        summary=commit["summary"],
                        message=html.escape(commit["message"]),
                        committedDateTime=commit["committed_datetime"],
                    )
                    for commitHash, commit in blame_info["commits"].items()
                }

                blame_data = [BlameData(
                    startLine=b["from"],
                    endLine=b["to"],
                    commitHash=b["commit"]) for b in blame_info["blame"]]

                return BlameInfo(
                    commits=commits,
                    blame=blame_data)
            except Exception:
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    "Failed to get blame information for file id: " + fileId)

    @exc_to_thrift_reqfail
    @timeit
    def getLinesInSourceFileContents(self, lines_in_files_requested, encoding):
        self.__require_view()
        with DBSession(self._Session) as session:
            res = defaultdict(lambda: defaultdict(str))
            for lines_in_file in lines_in_files_requested:
                if lines_in_file.fileId is None:
                    LOG.warning("File content requested without a fileId.")
                    LOG.warning(lines_in_file)
                    continue
                sourcefile = session.query(File).get(lines_in_file.fileId)
                cont = session.query(FileContent).get(sourcefile.content_hash)
                lines = zlib.decompress(
                    cont.content).decode('utf-8', 'ignore').split('\n')
                for line in lines_in_file.lines:
                    content = '' if len(lines) < line else lines[line - 1]
                    if encoding == Encoding.BASE64:
                        content = convert.to_b64(content)
                    res[lines_in_file.fileId][line] = content
            return res

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerCounts(self, run_ids, report_filter, cmp_data, limit,
                         offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()

        limit = verify_limit_range(limit)

        results = []
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(func.max(Report.checker_id).label(
                    'checker_id'),
                    func.max(Report.severity).label(
                    'severity'),
                    Report.bug_id)
            else:
                q = session.query(Report.checker_id,
                                  Report.severity,
                                  func.count(Report.id))

            q = apply_report_filter(q, filter_expression, join_tables)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                unique_checker_q = session.query(q.c.checker_id,
                                                 func.max(q.c.severity),
                                                 func.count(q.c.bug_id)) \
                    .group_by(q.c.checker_id) \
                    .order_by(q.c.checker_id)
            else:
                unique_checker_q = q.group_by(Report.checker_id,
                                              Report.severity) \
                    .order_by(Report.checker_id)

            if limit:
                unique_checker_q = unique_checker_q.limit(limit).offset(offset)

            for name, severity, count in unique_checker_q:
                checker_count = CheckerCount(name=name,
                                             severity=severity,
                                             count=count)
                results.append(checker_count)
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getAnalyzerNameCounts(self, run_ids, report_filter, cmp_data, limit,
                              offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()

        limit = verify_limit_range(limit)

        results = {}
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(func.max(Report.analyzer_name).label(
                    'analyzer_name'),
                    Report.bug_id)
            else:
                q = session.query(Report.analyzer_name,
                                  func.count(Report.id))

            q = apply_report_filter(q, filter_expression, join_tables)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                analyzer_name_q = session.query(q.c.analyzer_name,
                                                func.count(q.c.bug_id)) \
                    .group_by(q.c.analyzer_name) \
                    .order_by(q.c.analyzer_name)
            else:
                analyzer_name_q = q.group_by(Report.analyzer_name) \
                    .order_by(Report.analyzer_name)

            if limit:
                analyzer_name_q = analyzer_name_q.limit(limit).offset(offset)

            for name, count in analyzer_name_q:
                results[name] = count

        return results

    @exc_to_thrift_reqfail
    @timeit
    def getSeverityCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()
        results = {}
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(func.max(Report.severity).label('severity'),
                                  Report.bug_id)
            else:
                q = session.query(Report.severity,
                                  func.count(Report.id))

            q = apply_report_filter(q, filter_expression, join_tables)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                severities = session.query(q.c.severity,
                                           func.count(q.c.bug_id)) \
                    .group_by(q.c.severity)
            else:
                severities = q.group_by(Report.severity)

            results = dict(severities)
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerMsgCounts(self, run_ids, report_filter, cmp_data, limit,
                            offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()

        limit = verify_limit_range(limit)

        results = {}
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(func.max(Report.checker_message).label(
                    'checker_message'),
                    Report.bug_id)
            else:
                q = session.query(Report.checker_message,
                                  func.count(Report.id))

            q = apply_report_filter(q, filter_expression, join_tables)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                checker_messages = session.query(q.c.checker_message,
                                                 func.count(q.c.bug_id)) \
                    .group_by(q.c.checker_message) \
                    .order_by(q.c.checker_message)
            else:
                checker_messages = q.group_by(Report.checker_message) \
                                    .order_by(Report.checker_message)

            if limit:
                checker_messages = checker_messages.limit(limit).offset(offset)

            results = dict(checker_messages.all())
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getReviewStatusCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()
        results = defaultdict(int)
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(
                    Report.bug_id,
                    Report.review_status,
                    func.count(Report.bug_id))
            else:
                q = session.query(
                    func.max(Report.bug_id),
                    Report.review_status,
                    func.count(Report.id))

            q = apply_report_filter(q, filter_expression, join_tables)

            if is_unique:
                review_statuses = q.group_by(Report.bug_id,
                                             Report.review_status)
            else:
                review_statuses = q.group_by(Report.review_status)

            for _, rev_status, count in review_statuses:
                rev_status = review_status_enum(rev_status)
                results[rev_status] += count

        return results

    @exc_to_thrift_reqfail
    @timeit
    def getFileCounts(self, run_ids, report_filter, cmp_data, limit, offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()

        limit = verify_limit_range(limit)

        results = {}
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            stmt = session.query(Report.bug_id,
                                 Report.file_id)
            stmt = apply_report_filter(stmt, filter_expression,
                                       join_tables)

            if report_filter is not None and report_filter.isUnique:
                stmt = stmt.group_by(Report.bug_id, Report.file_id)

            stmt = stmt.subquery()

            # When using pg8000, 1 cannot be passed as parameter to the count
            # function. This is the reason why we have to convert it to
            # Integer (see: https://github.com/mfenniak/pg8000/issues/110)
            count_int = cast(1, sqlalchemy.Integer)
            report_count = session.query(stmt.c.file_id,
                                         func.count(count_int).label(
                                             'report_count')) \
                .group_by(stmt.c.file_id)

            if limit:
                report_count = report_count.limit(limit).offset(offset)

            report_count = report_count.subquery()
            file_paths = session.query(File.filepath,
                                       report_count.c.report_count) \
                .join(report_count,
                      report_count.c.file_id == File.id)

            for fp, count in file_paths:
                results[fp] = count
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunHistoryTagCounts(self, run_ids, report_filter, cmp_data, limit,
                               offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()

        limit = verify_limit_range(limit)

        results = []
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            tag_run_ids = session.query(RunHistory.run_id.distinct())

            if run_ids:
                tag_run_ids = tag_run_ids.filter(
                    RunHistory.run_id.in_(run_ids))

            tag_run_ids = tag_run_ids.subquery()

            report_cnt_q = session.query(Report.run_id,
                                         Report.bug_id,
                                         Report.detected_at,
                                         Report.fixed_at)
            report_cnt_q = apply_report_filter(
                report_cnt_q, filter_expression, join_tables)
            report_cnt_q = report_cnt_q.filter(
                Report.run_id.in_(tag_run_ids)).subquery()

            is_unique = report_filter is not None and report_filter.isUnique
            count_expr = func.count(report_cnt_q.c.bug_id if not is_unique
                                    else report_cnt_q.c.bug_id.distinct())

            count_q = session.query(RunHistory.id.label('run_history_id'),
                                    count_expr.label('report_count')) \
                .outerjoin(report_cnt_q,
                           report_cnt_q.c.run_id == RunHistory.run_id) \
                .filter(get_open_reports_date_filter_query(report_cnt_q.c)) \
                .group_by(RunHistory.id) \
                .subquery()

            tag_q = session.query(RunHistory.run_id.label('run_id'),
                                  RunHistory.id.label('run_history_id'))

            if run_ids:
                tag_q = tag_q.filter(RunHistory.run_id.in_(run_ids))

            if report_filter and report_filter.runTag is not None:
                tag_q = tag_q.filter(RunHistory.id.in_(report_filter.runTag))

            tag_q = tag_q.subquery()

            q = session.query(tag_q.c.run_history_id,
                              func.max(Run.id),
                              func.max(Run.name).label('run_name'),
                              func.max(RunHistory.id),
                              func.max(RunHistory.time),
                              func.max(RunHistory.version_tag),
                              func.max(count_q.c.report_count)) \
                .outerjoin(RunHistory,
                           RunHistory.id == tag_q.c.run_history_id) \
                .outerjoin(Run, Run.id == tag_q.c.run_id) \
                .outerjoin(count_q,
                           count_q.c.run_history_id == RunHistory.id) \
                .group_by(tag_q.c.run_history_id, RunHistory.time) \
                .order_by(RunHistory.time.desc())

            if limit:
                q = q.limit(limit).offset(offset)

            for _, run_id, run_name, tag_id, version_time, tag, count in q:
                results.append(RunTagCount(id=tag_id,
                                           time=str(version_time),
                                           name=tag,
                                           runName=run_name,
                                           runId=run_id,
                                           count=count if count else 0))
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getDetectionStatusCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()
        results = {}
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            count_expr = func.count(literal_column('*'))

            q = session.query(Report.detection_status,
                              count_expr)

            q = apply_report_filter(q, filter_expression, join_tables)

            detection_stats = q.group_by(Report.detection_status).all()

            results = dict(detection_stats)
            results = {
                detection_status_enum(k): v for k,
                v in results.items()}

        return results

    @exc_to_thrift_reqfail
    @timeit
    def getFailedFilesCount(self, run_ids):
        """
        Count the number of uniqued failed files in the latest storage of each
        given run. If the run id list is empty the number of failed files will
        be counted for all of the runs.
        """
        # Unfortunately we can't distinct the failed file paths by using SQL
        # queries because the list of failed files for a run / analyzer are
        # stored in one column in a compressed way. For this reason we need to
        # decompress the value in the Python code before uniqueing.
        return len(self.getFailedFiles(run_ids).keys())

    @exc_to_thrift_reqfail
    @timeit
    def getFailedFiles(self, run_ids):
        """
        Get files which failed to analyze in the latest storage of the given
        runs. For each files it will return a list where each element contains
        information in which run the failure happened.
        """
        self.__require_view()

        res = defaultdict(list)
        with DBSession(self._Session) as session:
            query, sub_q = get_failed_files_query(
                session, run_ids, [AnalyzerStatistic.failed_files, Run.name],
                [RunHistory.run_id])

            query = query \
                .outerjoin(Run, Run.id == sub_q.c.run_id) \
                .filter(AnalyzerStatistic.failed_files.isnot(None))

            for failed_files, run_name in query.all():
                failed_files = zlib.decompress(failed_files).decode('utf-8')

                for failed_file in failed_files.split('\n'):
                    already_exists = \
                        any(i.runName == run_name for i in res[failed_file])

                    if not already_exists:
                        res[failed_file].append(
                            ttypes.AnalysisFailureInfo(runName=run_name))

        return res

    # -----------------------------------------------------------------------
    @timeit
    def getPackageVersion(self):
        return self.__package_version

    # -----------------------------------------------------------------------
    @exc_to_thrift_reqfail
    @timeit
    def removeRunResults(self, run_ids):
        self.__require_store()

        failed = False
        for run_id in run_ids:
            try:
                self.removeRun(run_id, None)
            except Exception as ex:
                LOG.error("Failed to remove run: %s", run_id)
                LOG.error(ex)
                failed = True
        return not failed

    def _removeReports(self, session, report_ids,
                       chunk_size=SQLITE_MAX_VARIABLE_NUMBER):
        """
        Removing reports in chunks.
        """
        for r_ids in util.chunks(iter(report_ids), chunk_size):
            session.query(Report) \
                .filter(Report.id.in_(r_ids)) \
                .delete(synchronize_session=False)

    @exc_to_thrift_reqfail
    @timeit
    def removeRunReports(self, run_ids, report_filter, cmp_data):
        self.__require_store()

        if not run_ids:
            run_ids = []

        if cmp_data and cmp_data.runIds:
            run_ids.extend(cmp_data.runIds)

        with DBSession(self._Session) as session:
            check_remove_runs_lock(session, run_ids)

            try:
                filter_expression, join_tables = process_report_filter(
                    session, run_ids, report_filter, cmp_data)

                q = session.query(Report.id)
                q = apply_report_filter(q, filter_expression, join_tables)

                reports_to_delete = [r[0] for r in q]
                if reports_to_delete:
                    self._removeReports(session, reports_to_delete)

                session.commit()
                session.close()

                LOG.info("The following reports were removed by '%s': %s",
                         self._get_username(), reports_to_delete)
            except Exception as ex:
                session.rollback()
                LOG.error("Database cleanup failed.")
                LOG.error(ex)
                return False

        # Remove unused comments and unused analysis info from the database.
        # Originally db_cleanup.remove_unused_data() was used here which
        # removes unused file entries too. However, removing files at the same
        # time with a concurrently ongoing storage may result in a foreign key
        # constraint error. An alternative solution can be adding the last
        # access timestamp to file entries to delay their removal (and avoid
        # removing frequently accessed files). The same comment applies to
        # removeRun() function.
        db_cleanup.remove_unused_comments(self._Session)
        db_cleanup.remove_unused_analysis_info(self._Session)

        return True

    @exc_to_thrift_reqfail
    @timeit
    def removeRun(self, run_id, run_filter):
        self.__require_store()

        # Remove the whole run.
        with DBSession(self._Session) as session:
            check_remove_runs_lock(session, [run_id])

            if not run_filter:
                run_filter = RunFilter(ids=[run_id])

            q = process_run_filter(session, session.query(Run), run_filter)

            # q.delete(synchronize_session=False) could also be used here,
            # however, a run deletion tends to be a slow operation due to
            # cascades and such. Deleting runs in separate transactions don't
            # exceed a potential statement timeout threshold in a DBMS.
            for run in q.all():
                session.delete(run)
                session.commit()

            session.close()

            runs = run_filter.names if run_filter.names else run_filter.ids
            LOG.info("Runs '%s' were removed by '%s'.", runs,
                     self._get_username())

        # Decrement the number of runs but do not update the latest storage
        # date.
        self._set_run_data_for_curr_product(-1)

        # Remove unused comments and unused analysis info from the database.
        # Originally db_cleanup.remove_unused_data() was used here which
        # removes unused file entries tool. However removing files at the same
        # time with a storage concurrently results foreign key constraint
        # error. An alternative solution can be adding a timestamp to file
        # entries to delay their removal. The same comment applies to
        # removeRunReports() function.
        db_cleanup.remove_unused_comments(self._Session)
        db_cleanup.remove_unused_analysis_info(self._Session)

        return True

    @exc_to_thrift_reqfail
    @timeit
    def updateRunData(self, run_id, new_run_name):
        self.__require_store()

        if not new_run_name:
            msg = 'No new run name was given to update the run.'
            LOG.error(msg)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL, msg)

        with DBSession(self._Session) as session:
            check_new_run_name = session.query(Run) \
                .filter(Run.name == new_run_name) \
                .all()
            if check_new_run_name:
                msg = "New run name '" + new_run_name + "' already exists."
                LOG.error(msg)

                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

            run_data = session.query(Run).get(run_id)
            if run_data:
                old_run_name = run_data.name
                run_data.name = new_run_name
                session.add(run_data)
                session.commit()

                LOG.info("Run name '%s' (%d) was changed to %s by '%s'.",
                         old_run_name, run_id, new_run_name,
                         self._get_username())

                return True
            else:
                msg = 'Run id ' + str(run_id) + \
                      ' was not found in the database.'
                LOG.error(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

        return True

    @exc_to_thrift_reqfail
    def getSuppressFile(self):
        """
        DEPRECATED the server is not started with a suppress file anymore.
        Returning empty string.
        """
        self.__require_access()
        return ''

    @exc_to_thrift_reqfail
    @timeit
    def addSourceComponent(self, name, value, description):
        """
        Adds a new source if it does not exist or updates an old one.
        """
        self.__require_admin()
        with DBSession(self._Session) as session:
            component = session.query(SourceComponent).get(name)
            user = self._auth_session.user if self._auth_session else None

            if component:
                component.value = value.encode('utf-8')
                component.description = description
                component.user = user
            else:
                component = SourceComponent(name,
                                            value.encode('utf-8'),
                                            description,
                                            user)

            session.add(component)
            session.commit()

            return True

    @exc_to_thrift_reqfail
    @timeit
    def getSourceComponents(self, component_filter):
        """
        Returns the available source components.
        """
        self.__require_view()
        with DBSession(self._Session) as session:
            q = session.query(SourceComponent)

            if component_filter:
                sql_component_filter = [SourceComponent.name.ilike(conv(cf))
                                        for cf in component_filter]
                q = q.filter(*sql_component_filter)

            q = q.order_by(SourceComponent.name)

            components = [SourceComponentData(c.name, c.value.decode('utf-8'),
                                              c.description) for c in q]

            # If no filter is set or the auto generated component name can
            # be found in the filter list we will return with this
            # component too.
            if not component_filter or \
                    GEN_OTHER_COMPONENT_NAME in component_filter:
                component_other = \
                    SourceComponentData(GEN_OTHER_COMPONENT_NAME, None,
                                        "Special auto-generated source "
                                        "component which contains files that "
                                        "are uncovered by the rest of the "
                                        "components.")

                components.append(component_other)

            return components

    @exc_to_thrift_reqfail
    @timeit
    def removeSourceComponent(self, name):
        """
        Removes a source component.
        """
        self.__require_admin()

        with DBSession(self._Session) as session:
            component = session.query(SourceComponent).get(name)
            if component:
                session.delete(component)
                session.commit()
                LOG.info("Source component '%s' has been removed by '%s'",
                         name, self._get_username())
                return True
            else:
                msg = 'Source component ' + str(name) + \
                      ' was not found in the database.'
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def getMissingContentHashes(self, file_hashes):
        self.__require_store()

        if not file_hashes:
            return []

        with DBSession(self._Session) as session:

            q = session.query(FileContent) \
                .options(sqlalchemy.orm.load_only('content_hash')) \
                .filter(FileContent.content_hash.in_(file_hashes))

            return list(set(file_hashes) -
                        set([fc.content_hash for fc in q]))

    @exc_to_thrift_reqfail
    @timeit
    def getMissingContentHashesForBlameInfo(self, file_hashes):
        self.__require_store()

        if not file_hashes:
            return []

        with DBSession(self._Session) as session:

            q = session.query(FileContent) \
                .options(sqlalchemy.orm.load_only('content_hash')) \
                .filter(FileContent.content_hash.in_(file_hashes)) \
                .filter(FileContent.blame_info.isnot(None))

            return list(set(file_hashes) -
                        set([fc.content_hash for fc in q]))

    @exc_to_thrift_reqfail
    @timeit
    def massStoreRun(self, name, tag, version, b64zip, force,
                     trim_path_prefixes, description):
        self.__require_store()

        from codechecker_server.api.mass_store_run import MassStoreRun
        m = MassStoreRun(self, name, tag, version, b64zip, force,
                         trim_path_prefixes, description)
        return m.store()

    @exc_to_thrift_reqfail
    @timeit
    def allowsStoringAnalysisStatistics(self):
        self.__require_store()

        return True if self._manager.get_analysis_statistics_dir() else False

    @exc_to_thrift_reqfail
    @timeit
    def getAnalysisStatisticsLimits(self):
        self.__require_store()

        cfg = dict()

        # Get the limit of failure zip size.
        failure_zip_size = self._manager.get_failure_zip_size()
        if failure_zip_size:
            cfg[ttypes.StoreLimitKind.FAILURE_ZIP_SIZE] = failure_zip_size

        # Get the limit of compilation database size.
        compilation_database_size = \
            self._manager.get_compilation_database_size()
        if compilation_database_size:
            cfg[ttypes.StoreLimitKind.COMPILATION_DATABASE_SIZE] = \
                compilation_database_size

        return cfg

    @exc_to_thrift_reqfail
    @timeit
    def storeAnalysisStatistics(self, run_name, b64zip):
        self.__require_store()

        report_dir_store = self._manager.get_analysis_statistics_dir()
        if report_dir_store:
            try:
                product_dir = os.path.join(report_dir_store,
                                           self._product.endpoint)
                # Create report store directory.
                if not os.path.exists(product_dir):
                    os.makedirs(product_dir, mode=stat.S_IRWXU | stat.S_IRGRP)

                # Removes and replaces special characters in the run name.
                run_name = slugify(run_name)
                run_zip_file = os.path.join(product_dir, run_name + '.zip')
                with open(run_zip_file, 'wb') as run_zip:
                    run_zip.write(zlib.decompress(
                        base64.b64decode(b64zip.encode('utf-8'))))

                # Change permission, so only current user and group have access
                # to this file.
                os.chmod(
                    run_zip_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)

                return True
            except Exception as ex:
                LOG.error(str(ex))
                return False

        return False

    @exc_to_thrift_reqfail
    @timeit
    def getAnalysisStatistics(self, run_id, run_history_id):
        self.__require_view()

        analyzer_statistics = {}

        with DBSession(self._Session) as session:
            run_ids = None if run_id is None else [run_id]
            run_history_ids = None if run_history_id is None \
                else [run_history_id]

            query = get_analysis_statistics_query(
                session, run_ids, run_history_ids)

            for stat, run_id in query:
                failed_files = zlib.decompress(stat.failed_files).decode(
                    'utf-8').split('\n') if stat.failed_files else []
                analyzer_version = zlib.decompress(
                    stat.version).decode('utf-8') if stat.version else None

                analyzer_statistics[stat.analyzer_type] = \
                    ttypes.AnalyzerStatistics(version=analyzer_version,
                                              failed=stat.failed,
                                              failedFilePaths=failed_files,
                                              successful=stat.successful)
        return analyzer_statistics

    @exc_to_thrift_reqfail
    @timeit
    def exportData(self, run_filter):
        self.__require_view()

        with DBSession(self._Session) as session:

            # Logic for getting comments
            comment_data_list = defaultdict(list)
            comment_query = session.query(Comment, Report.bug_id) \
                .outerjoin(Report, Report.bug_id == Comment.bug_hash) \
                .order_by(Comment.created_at.desc(), Comment.id.desc())

            if run_filter:
                comment_query = process_run_filter(session, comment_query,
                                                   run_filter) \
                    .outerjoin(Run, Report.run_id == Run.id)

            for data, report_id in comment_query:
                comment_data = ttypes.CommentData(
                    id=data.id,
                    author=data.author,
                    message=html.unescape(data.message.decode('utf-8')),
                    createdAt=str(data.created_at),
                    kind=data.kind)
                comment_data_list[report_id].append(comment_data)

            # Logic for getting review status
            review_data_list = {}
            review_query = session.query(Report) \
                .filter(Report.review_status != "unreviewed") \
                .order_by(Report.review_status_date)

            if run_filter:
                review_query = process_run_filter(session, review_query,
                                                  run_filter) \
                    .outerjoin(Run, Report.run_id == Run.id)

            for report in review_query:
                review_data = create_review_data(
                    report.review_status,
                    report.review_status_message,
                    report.review_status_author,
                    report.review_status_date,
                    report.review_status_is_in_source)
                review_data_list[report.bug_id] = review_data

        return ExportData(comments=comment_data_list,
                          reviewData=review_data_list)

    @exc_to_thrift_reqfail
    @timeit
    def importData(self, exportData):
        self.__require_admin()
        with DBSession(self._Session) as session:

            # Logic for importing comments
            comment_bug_ids = list(exportData.comments.keys())
            comment_query = session.query(Comment) \
                .filter(Comment.bug_hash.in_(comment_bug_ids)) \
                .order_by(Comment.created_at.desc())
            comments_in_db = defaultdict(list)
            for comment in comment_query:
                comments_in_db[comment.bug_hash].append(comment)
            for bug_hash, comments in exportData.comments.items():
                db_comments = comments_in_db[bug_hash]
                for comment in comments:
                    date = datetime.strptime(comment.createdAt,
                                             '%Y-%m-%d %H:%M:%S.%f')
                    message = comment.message.encode('utf-8') \
                        if comment.message else b''
                    # See if the comment is already in the database.
                    if any(c.created_at == date and
                           c.kind == comment.kind and
                           c.message == message for c in db_comments):
                        continue
                    c = Comment(bug_hash, comment.author, message,
                                comment.kind, date)
                    session.add(c)

            # Logic for importing review status
            review_bug_ids = list(exportData.reviewData.keys())
            review_query = session.query(ReviewStatus) \
                .filter(ReviewStatus.bug_hash.in_(review_bug_ids)) \
                .order_by(ReviewStatus.date.desc())
            db_review_data = {}
            for review_status in review_query:
                db_review_data[review_status.bug_hash] = review_status
            for bug_hash, imported_review in exportData.reviewData.items():
                db_status = db_review_data.get(bug_hash)
                # The status is up-to-date.
                if db_status and str(db_status.date) == imported_review.date:
                    continue
                date = datetime.strptime(imported_review.date,
                                         '%Y-%m-%d %H:%M:%S.%f')
                self._setReviewStatus(session,
                                      bug_hash,
                                      imported_review.status,
                                      imported_review.comment,
                                      date)

            session.commit()
            return True

    @exc_to_thrift_reqfail
    @timeit
    def addCleanupPlan(self, name, description, dueDate):
        self.__require_admin()

        with DBSession(self._Session) as session:
            cleanup_plan = session.query(CleanupPlan) \
                .filter(CleanupPlan.name == name) \
                .one_or_none()

            if cleanup_plan:
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    f"Cleanup plan '{name}' already exists.")

            cleanup_plan = CleanupPlan(name)
            cleanup_plan.description = description
            cleanup_plan.due_date = \
                datetime.fromtimestamp(dueDate) if dueDate else None

            session.add(cleanup_plan)
            session.commit()

            LOG.info("New cleanup plan '%s' has been created by '%s'",
                     name, self._get_username())

            return cleanup_plan.id

    @exc_to_thrift_reqfail
    @timeit
    def updateCleanupPlan(self, cleanup_plan_id, name, description, dueDate):
        self.__require_admin()

        with DBSession(self._Session) as session:
            cleanup_plan = get_cleanup_plan(session, cleanup_plan_id)
            cleanup_plan.name = name
            cleanup_plan.description = description
            cleanup_plan.due_date = \
                datetime.fromtimestamp(dueDate) if dueDate else None

            session.add(cleanup_plan)
            session.commit()

            LOG.info("Cleanup plan '%d' has been updated by '%s'",
                     cleanup_plan_id, self._get_username())

            return True

    @exc_to_thrift_reqfail
    @timeit
    def getCleanupPlans(self, cleanup_plan_filter):
        self.__require_view()
        with DBSession(self._Session) as session:
            q = session \
                .query(CleanupPlan) \
                .order_by(CleanupPlan.name)

            if cleanup_plan_filter:
                if cleanup_plan_filter.ids:
                    q = q.filter(CleanupPlan.id.in_(
                        cleanup_plan_filter.ids))

                if cleanup_plan_filter.names:
                    q = q.filter(CleanupPlan.name.in_(
                        cleanup_plan_filter.names))

                if cleanup_plan_filter.isOpen is not None:
                    if cleanup_plan_filter.isOpen:
                        q = q.filter(CleanupPlan.closed_at.is_(None))
                    else:
                        q = q.filter(CleanupPlan.closed_at.isnot(None))

            cleanup_plans = q.all()

            cleanup_plan_hashes = get_cleanup_plan_report_hashes(
                session, [c.id for c in cleanup_plans])

            return [ttypes.CleanupPlan(
                id=cp.id,
                name=cp.name,
                description=cp.description,
                dueDate=int(time.mktime(
                    cp.due_date.timetuple())) if cp.due_date else None,
                closedAt=int(time.mktime(
                    cp.closed_at.timetuple())) if cp.closed_at else None,
                reportHashes=cleanup_plan_hashes[cp.id]) for cp in q]

    @exc_to_thrift_reqfail
    @timeit
    def removeCleanupPlan(self, cleanup_plan_id):
        self.__require_admin()
        with DBSession(self._Session) as session:
            cleanup_plan = get_cleanup_plan(session, cleanup_plan_id)
            name = cleanup_plan.name

            session.delete(cleanup_plan)
            session.commit()

            LOG.info("Cleanup plan '%s' has been removed by '%s'",
                     name, self._get_username())

            return True

    @exc_to_thrift_reqfail
    @timeit
    def closeCleanupPlan(self, cleanup_plan_id):
        self.__require_admin()

        with DBSession(self._Session) as session:
            cleanup_plan = get_cleanup_plan(session, cleanup_plan_id)

            cleanup_plan.closed_at = datetime.now()
            session.add(cleanup_plan)
            session.commit()

            LOG.info("Cleanup plan '%s' has been closed by '%s'",
                     cleanup_plan.name, self._get_username())

            return True

    @exc_to_thrift_reqfail
    @timeit
    def reopenCleanupPlan(self, cleanup_plan_id):
        self.__require_admin()

        with DBSession(self._Session) as session:
            cleanup_plan = get_cleanup_plan(session, cleanup_plan_id)

            cleanup_plan.closed_at = None
            session.add(cleanup_plan)
            session.commit()
            LOG.info("Cleanup plan '%s' has been reopened by '%s'",
                     cleanup_plan.name, self._get_username())
            return True

    @exc_to_thrift_reqfail
    @timeit
    def setCleanupPlan(self, cleanup_plan_id, reportHashes):
        self.__require_admin()

        with DBSession(self._Session) as session:
            cleanup_plan = get_cleanup_plan(session, cleanup_plan_id)

            q = session \
                .query(CleanupPlanReportHash.bug_hash) \
                .filter(
                    CleanupPlanReportHash.cleanup_plan_id == cleanup_plan.id) \
                .filter(CleanupPlanReportHash.bug_hash.in_(reportHashes))
            new_report_hashes = set(reportHashes) - set(b[0] for b in q)

            for report_hash in new_report_hashes:
                session.add(CleanupPlanReportHash(
                    cleanup_plan_id=cleanup_plan.id, bug_hash=report_hash))

            session.commit()

            return True

    @exc_to_thrift_reqfail
    @timeit
    def unsetCleanupPlan(self, cleanup_plan_id, reportHashes):
        self.__require_admin()

        with DBSession(self._Session) as session:
            cleanup_plan = get_cleanup_plan(session, cleanup_plan_id)

            session \
                .query(CleanupPlanReportHash) \
                .filter(
                    CleanupPlanReportHash.cleanup_plan_id == cleanup_plan.id) \
                .filter(CleanupPlanReportHash.bug_hash.in_(reportHashes)) \
                .delete(synchronize_session=False)

            session.commit()
            session.close()

            return True
