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

from copy import deepcopy
from collections import OrderedDict, defaultdict, namedtuple
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import sqlalchemy
from sqlalchemy.sql.expression import or_, and_, not_, func, \
    asc, desc, union_all, select, bindparam, literal_column, case, cast
from sqlalchemy.orm import contains_eager

import codechecker_api_shared
from codechecker_api.codeCheckerDBAccess_v6 import constants, ttypes
from codechecker_api.codeCheckerDBAccess_v6.ttypes import \
    AnalysisInfoFilter, AnalysisInfoChecker as API_AnalysisInfoChecker, \
    BlameData, BlameInfo, BugPathPos, \
    CheckerCount, CheckerStatusVerificationDetail, Commit, CommitAuthor, \
    CommentData, \
    DetectionStatus, DiffType, \
    Encoding, ExportData, \
    Order, \
    ReportData, ReportDetails, ReportStatus, ReviewData, ReviewStatusRule, \
    ReviewStatusRuleFilter, ReviewStatusRuleSortMode, \
    ReviewStatusRuleSortType, RunData, RunFilter, RunHistoryData, \
    RunReportCount, RunSortType, RunTagCount, \
    ReviewStatus as API_ReviewStatus, \
    SourceComponentData, SourceFileData, SortMode, SortType

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
    AnalysisInfo, AnalysisInfoChecker as DB_AnalysisInfoChecker, \
    AnalyzerStatistic, \
    BugPathEvent, BugReportPoint, \
    CleanupPlan, CleanupPlanReportHash, Checker, Comment, \
    ExtendedReportData, \
    File, FileContent, \
    Report, ReportAnnotations, ReportAnalysisInfo, ReviewStatus, \
    Run, RunHistory, RunHistoryAnalysisInfo, RunLock, \
    SourceComponent

from .thrift_enum_helper import detection_status_enum, \
    detection_status_str, report_status_enum, \
    review_status_enum, review_status_str, report_extended_data_type_enum

# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name

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

    assert False, f"Unknown ttypes.CommentKind: {kind}"


def comment_kind_to_thrift_type(kind):
    """ Convert the given comment kind from Python enum to Thrift type. """
    if kind == CommentKindValue.USER:
        return ttypes.CommentKind.USER
    elif kind == CommentKindValue.SYSTEM:
        return ttypes.CommentKind.SYSTEM

    assert False, f"Unknown CommentKindValue: {kind}"


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


def exc_to_thrift_reqfail(function):
    """
    Convert internal exceptions to RequestFailed exception
    which can be sent back on the thrift connections.
    """
    func_name = function.__name__

    def wrapper(*args, **kwargs):
        try:
            res = function(*args, **kwargs)
            return res

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            # Convert SQLAlchemy exceptions.
            msg = str(alchemy_ex)
            import traceback
            traceback.print_exc()
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


def process_report_filter(
    session,
    run_ids,
    report_filter,
    cmp_data=None,
    keep_all_annotations=False
):
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
        if report_filter.fileMatchesAnyPoint:
            AND.append(Report.id.in_(get_reports_by_files(
                session,
                report_filter.filepath)))
        else:
            OR = [File.filepath.ilike(conv(fp))
                  for fp in report_filter.filepath]

            AND.append(or_(*OR))
            join_tables.append(File)

    if report_filter.checkerMsg:
        OR = [Report.checker_message.ilike(conv(cm))
              for cm in report_filter.checkerMsg]
        AND.append(or_(*OR))

    if report_filter.analyzerNames or report_filter.checkerName \
            or report_filter.severity:
        if report_filter.analyzerNames:
            OR = [Checker.analyzer_name.ilike(conv(an))
                  for an in report_filter.analyzerNames]
            AND.append(or_(*OR))

        if report_filter.checkerName:
            OR = [Checker.checker_name.ilike(conv(cn))
                  for cn in report_filter.checkerName]
            AND.append(or_(*OR))

        if report_filter.severity:
            AND.append(Checker.severity.in_(report_filter.severity))

        join_tables.append(Checker)

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

    if report_filter.reportStatus:
        dst = list(map(detection_status_str,
                       (DetectionStatus.NEW,
                        DetectionStatus.UNRESOLVED,
                        DetectionStatus.REOPENED)))
        rst = list(map(review_status_str,
                       (API_ReviewStatus.UNREVIEWED,
                        API_ReviewStatus.CONFIRMED)))

        OR = []
        filter_query = and_(
            Report.review_status.in_(rst),
            Report.detection_status.in_(dst)
        )
        if ReportStatus.OUTSTANDING in report_filter.reportStatus:
            OR.append(filter_query)

        if ReportStatus.CLOSED in report_filter.reportStatus:
            OR.append(not_(filter_query))

        AND.append(or_(*OR))

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
        if report_filter.componentMatchesAnyPoint:
            AND.append(Report.id.in_(get_reports_by_components(
                session,
                report_filter.componentNames)))
        else:
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

    if report_filter.annotations is not None:
        annotations = defaultdict(list)
        for annotation in report_filter.annotations:
            annotations[annotation.first].append(annotation.second)

        OR = []
        for key, values in annotations.items():
            if keep_all_annotations:
                OR.append(or_(
                    ReportAnnotations.key != key,
                    *[ReportAnnotations.value.ilike(conv(v))
                      for v in values]))
            else:
                OR.append(and_(
                    ReportAnnotations.key == key,
                    or_(*[ReportAnnotations.value.ilike(conv(v))
                          for v in values])) if values else and_(
                              ReportAnnotations.key == key))

        AND.append(or_(*OR))

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
    For further information see the documentation of
    filter_open_reports_in_tags_old().
    """

    if run_ids:
        results = results.filter(Report.run_id.in_(run_ids))

    if tag_ids:
        results = results.outerjoin(
            RunHistory, RunHistory.run_id == Report.run_id) \
            .filter(RunHistory.id.in_(tag_ids)) \
            .filter(get_open_reports_date_filter_query())

    return results


def filter_open_reports_in_tags_old(results, run_ids, tag_ids):
    """
    Adding filters on "results" query which filter on open reports in
    given runs and tags.

    This function is almost the same as filter_open_reports_in_tags() except
    that is uses get_open_reports_date_filter_query_old() for filtering open
    reports on a given date. This function is duplicated, because we didn't
    want to add an extra parameter for this function, but express the fact that
    an old client (i.e. API version before 6.50) should be given a different
    result set.
    This function and its duplicate are used in getDiffResultHash() which
    should behave differently when called by an old client. The reasons of this
    different behavior is described a previous commit
    (f6d0fedaf14b583df7bd26078a8a22b557be57c6) where another case of the issue
    was fixed.
    """

    if run_ids:
        results = results.filter(Report.run_id.in_(run_ids))

    if tag_ids:
        results = results.outerjoin(
            RunHistory, RunHistory.run_id == Report.run_id) \
            .filter(RunHistory.id.in_(tag_ids)) \
            .filter(get_open_reports_date_filter_query_old())

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

    if include:
        return or_(*[File.filepath.like(conv(fp)) for fp in include])
    elif skip:
        return and_(*[not_(File.filepath.like(conv(fp))) for fp in skip])

    return None


def get_reports_by_bugpath_filter(session, file_filter_q) -> Set[int]:
    """
    This function returns a query for report IDs that are related to any file
    described by the query in the second parameter, either because their bug
    path goes through these files, or there is any bug note, etc. in these
    files.
    """
    q_report = session.query(Report.id) \
        .join(File, File.id == Report.file_id) \
        .filter(file_filter_q)

    q_bugpathevent = session.query(BugPathEvent.report_id) \
        .join(File, File.id == BugPathEvent.file_id) \
        .filter(file_filter_q)

    q_bugreportpoint = session.query(BugReportPoint.report_id) \
        .join(File, File.id == BugReportPoint.file_id) \
        .filter(file_filter_q)

    q_extendedreportdata = session.query(ExtendedReportData.report_id) \
        .join(File, File.id == ExtendedReportData.file_id) \
        .filter(file_filter_q)

    return q_report.union(
        q_bugpathevent,
        q_extendedreportdata,
        q_bugreportpoint)


def get_reports_by_components(session, component_names: List[str]) -> Set[int]:
    """
    This function returns a set of report IDs that are related to any component
    in the second parameter, either because their bug path goes through these
    components, or there is any bug note, etc. in these components.
    """
    source_component_filter = \
        process_source_component_filter(session, component_names)
    return get_reports_by_bugpath_filter(session, source_component_filter)


def get_reports_by_files(session, files: List[str]) -> Set[int]:
    """
    This function returns a set of report IDs that are related to any file in
    the second parameter, either because their bug path goes through these
    files, or there is any bug note, etc. in these files.
    """
    file_filter = or_(*[File.filepath.ilike(conv(fp)) for fp in files])
    return get_reports_by_bugpath_filter(session, file_filter)


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

        return None

    queries = [get_query(n) for (n, ) in component_names]
    return and_(*queries)


def get_open_reports_date_filter_query(tbl=Report, date=RunHistory.time):
    """ Get open reports date filter. """
    return and_(tbl.detected_at <= date,
                or_(tbl.fixed_at.is_(None),
                    tbl.fixed_at > date))


def get_open_reports_date_filter_query_old(tbl=Report, date=RunHistory.time):
    """ Get open reports date filter.

    This function is a dupliation of get_open_reports_date_filter_query().
    For the reson of duplication see the documentation of
    filter_open_reports_in_tags_old().
    """
    return tbl.detected_at <= date


def get_diff_bug_id_query(session, run_ids, tag_ids, open_reports_date):
    """ Get bug id query for diff. """
    q = session.query(Report.bug_id.distinct())

    if run_ids:
        q = q.filter(Report.run_id.in_(run_ids))
        if not tag_ids and not open_reports_date:
            q = q.filter(Report.fixed_at.is_(None))

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


def apply_report_filter(q, filter_expression,
                        join_tables: List[Any],
                        already_joined_tables: Optional[List[Any]] = None):
    """
    Applies the given filter expression and joins the Checker, File, Run, and
    RunHistory tables if necessary based on join_tables parameter. If a table
    is already joined by the main query and this is indicated, that will not
    be joined by this function to prevent a "duplicate alias" error.
    """
    def needs_join(tbl):
        return tbl in join_tables and (already_joined_tables is None or
                                       tbl not in already_joined_tables)

    if needs_join(Checker):
        q = q.join(Checker, Report.checker_id == Checker.id)
    if needs_join(File):
        q = q.outerjoin(File, Report.file_id == File.id)
    if needs_join(Run):
        q = q.outerjoin(Run, Run.id == Report.run_id)
    if needs_join(RunHistory):
        q = q.outerjoin(RunHistory, RunHistory.run_id == Report.run_id)

    return q.filter(filter_expression)


def get_sort_map(sort_types, is_unique=False):
    # Get a list of sort_types which will be a nested ORDER BY.
    sort_type_map = {
        SortType.FILENAME: [(File.filepath, 'filepath'),
                            (Report.line, 'line')],
        SortType.BUG_PATH_LENGTH: [(Report.path_length, 'bug_path_length')],
        SortType.CHECKER_NAME: [(Checker.checker_name, 'checker_name')],
        SortType.SEVERITY: [(Checker.severity, 'severity')],
        SortType.REVIEW_STATUS: [(Report.review_status, 'rw_status')],
        SortType.DETECTION_STATUS: [(Report.detection_status, 'dt_status')],
        SortType.TIMESTAMP: [('annotation_timestamp', 'annotation_timestamp')],
        SortType.TESTCASE: [('annotation_testcase', 'annotation_testcase')]}

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
            f"are locked: {', '.join([r[0] for r in run_locks])}")


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
        return None

    for git_commit_url in git_commit_urls:
        m = git_commit_url["regex"].match(remote_url)
        if m:
            url = git_commit_url["url"]
            for key, value in m.groupdict().items():
                if value is not None:
                    url = url.replace(f"${key}", value)

            return url

    return None


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


def get_run_id_expression(session, report_filter):
    """
    Get run id or concatenated run id list by the unique mode and the DB type
    """
    if report_filter.isUnique:
        if session.bind.dialect.name == "postgresql":
            return func.string_agg(
                cast(Run.id, sqlalchemy.String).distinct(),
                ','
            ).label("run_id")
        return func.group_concat(Run.id.distinct()).label("run_id")
    return Run.id.label("run_id")


def get_is_enabled_case(subquery):
    """
    Creating a case statement to decide the report
    is enabled or not based on the detection status
    """
    detection_status_filters = subquery.c.detection_status.in_(list(
        map(detection_status_str,
            (DetectionStatus.OFF, DetectionStatus.UNAVAILABLE))
    ))

    return case(
        [(detection_status_filters, False)],
        else_=True
    )


def get_is_opened_case(subquery):
    """
    Creating a case statement to decide the report is opened or not
    based on the detection status and the review status
    """
    detection_statuses = (
        DetectionStatus.NEW,
        DetectionStatus.UNRESOLVED,
        DetectionStatus.REOPENED
    )
    review_statuses = (
        API_ReviewStatus.UNREVIEWED,
        API_ReviewStatus.CONFIRMED
    )
    detection_and_review_status_filters = [
        subquery.c.detection_status.in_(list(map(
            detection_status_str, detection_statuses))),
        subquery.c.review_status.in_(list(map(
            review_status_str, review_statuses)))
    ]
    return case(
        [(and_(*detection_and_review_status_filters), True)],
        else_=False
    )


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
                 client_version,
                 context):

        if not product:
            raise ValueError("Cannot initialize request handler without "
                             "a product to serve.")

        self._manager = manager
        self._product = product
        self._auth_session = auth_session
        self._config_database = config_database
        self.__package_version = package_version
        self.__client_version = client_version
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
            # FIXME: This log is likely overkill.
            LOG.info("Run counter in the config database was %s by %i.",
                     'increased' if inc_num_of_runs >= 0 else 'decreased',
                     abs(inc_num_of_runs))

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

            # Anonymous access is only allowed if authentication is
            # turned off
            if self._manager.is_enabled and not self._auth_session:
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You are not authorized to execute this action.")

            if not any(permissions.require_permission(
                    perm, args, self._auth_session)
                    for perm in required):
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
            analyzer_statistics = defaultdict(defaultdict)

            stat_q = get_analysis_statistics_query(session, run_filter.ids)
            for analyzer_stat, run_id in stat_q:
                analyzer_statistics[run_id][analyzer_stat.analyzer_type] = \
                    ttypes.AnalyzerStatistics(
                        failed=analyzer_stat.failed,
                        successful=analyzer_stat.successful)

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
                    command = zlib.decompress(cmd.analyzer_command) \
                        .decode("utf-8")

                    checkers_q = session \
                        .query(Checker.analyzer_name,
                               Checker.checker_name,
                               DB_AnalysisInfoChecker.enabled) \
                        .join(Checker, DB_AnalysisInfoChecker.checker_id ==
                              Checker.id) \
                        .filter(DB_AnalysisInfoChecker.
                                analysis_info_id == cmd.id)

                    checkers: Dict[str, Dict[str, API_AnalysisInfoChecker]] = \
                        defaultdict(dict)
                    for chk in checkers_q.all():
                        analyzer, checker, enabled = chk
                        checkers[analyzer][checker] = API_AnalysisInfoChecker(
                            enabled=enabled)

                    res.append(ttypes.AnalysisInfo(
                        analyzerCommand=html.escape(command),
                        checkers=checkers))

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
                for analyzer_stat in history.analyzer_statistics:
                    analyzer_statistics[analyzer_stat.analyzer_type] = \
                        ttypes.AnalyzerStatistics(
                            failed=analyzer_stat.failed,
                            successful=analyzer_stat.successful)

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
                .join(Checker, Report.checker_id == Checker.id) \
                .options(contains_eager(Report.checker)) \
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
                analyzerName=report.checker.analyzer_name,
                checkerId=report.checker.checker_name,
                severity=report.checker.severity,
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

        # FIXME: This getDiffResultsHash() function is returning a set of
        # reports based on what are they compared to in a "CodeChecker cmd
        # diff" command. Earlier this function didn't consider false positive
        # and intentional reports as closed reports. The client's behavior also
        # changed from CodeChecker 6.20.0 and this behavior is adapted to the
        # new server behavior. The problem is that the old client works
        # correcly only with the old server. For this reason we are branching
        # based on the client's version. We are having access to the Thrift
        # API version here. The behavior change happend in Thrift API version
        # 6.50.
        client_version = tuple(map(int, self.__client_version.split('.')))

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
                    .outerjoin(File, Report.file_id == File.id)

                if client_version >= (6, 50):
                    base_hashes = base_hashes.filter(
                        Report.detection_status.notin_(skip_statuses_str),
                        Report.fixed_at.is_(None))
                    base_hashes = filter_open_reports_in_tags(
                        base_hashes, run_ids, tag_ids)
                else:
                    base_hashes = base_hashes.filter(
                        Report.detection_status.notin_(skip_statuses_str))
                    base_hashes = filter_open_reports_in_tags_old(
                        base_hashes, run_ids, tag_ids)

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
                    for chunk in util.chunks(
                            iter(report_hashes), SQLITE_MAX_COMPOUND_SELECT):
                        new_hashes_query = union_all(*[
                            select([bindparam('bug_id' + str(i), h)
                                    .label('bug_id')])
                            for i, h in enumerate(chunk)])
                        q = select([new_hashes_query]).except_(base_hashes)
                        new_hashes.extend([res[0] for res in session.query(q)])

                    return new_hashes
            elif diff_type == DiffType.RESOLVED:
                results = session.query(Report.bug_id)

                if client_version >= (6, 50):
                    results = results.filter(or_(
                        Report.bug_id.notin_(report_hashes),
                        Report.fixed_at.isnot(None)))
                    results = filter_open_reports_in_tags(
                        results, run_ids, tag_ids)
                else:
                    results = results.filter(
                        Report.bug_id.notin_(report_hashes))
                    results = filter_open_reports_in_tags_old(
                        results, run_ids, tag_ids)

                return [res[0] for res in results]
            elif diff_type == DiffType.UNRESOLVED:
                results = session.query(Report.bug_id) \
                    .filter(Report.bug_id.in_(report_hashes))

                if client_version >= (6, 50):
                    results = results \
                        .filter(Report.detection_status.notin_(
                            skip_statuses_str)) \
                        .filter(Report.fixed_at.is_(None))
                    results = filter_open_reports_in_tags(
                        results, run_ids, tag_ids)
                else:
                    results = results.filter(
                        Report.detection_status.notin_(skip_statuses_str))
                    results = filter_open_reports_in_tags_old(
                        results, run_ids, tag_ids)

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

            # Extending "reports" table with report annotation columns.
            #
            # Suppose that we have these tables in the database:
            #
            # reports
            # =================
            # id, checker_id, ...
            # -------------------
            # 1,  123456,     ...
            # 2,  999999,     ...
            #
            # report_annotations
            # =======================
            # report_id, key,  value
            # -----------------------
            # 1,         key1, value1
            # 1,         key2, value2
            # 2,         key1, value3
            #
            # The resulting table should look like this:
            #
            # reports extended
            # ===================================================
            # id, checker_id, ..., annotation_key1, annotation_key2
            # ---------------------------------------------------
            # 1,  123456,     ..., value1,          value2
            # 2,  999999,     ..., value3,          NULL
            #
            # The SQL query which results this table is similar to this:
            #
            # SELECT
            #   <every column in "reports" table>,
            #   MAX(CASE WHEN report_annotations.key == <col1> THEN
            #       report_annotations.value END) AS annotation_<col1>
            #   MAX(CASE WHEN report_annotations.key == <col2> THEN
            #       report_annotations.value END) AS annotation_<col2>
            # FROM
            #   reports
            #   LEFT OUTER JOIN report_annotations ON
            #     report_annotations.report_id = reports.id
            # GROUP BY
            #   reports.id;
            #
            # <col1>, <col2>... are the distinct keys in table
            # "report_annotations". These are collected in a previous query.
            #
            # Since the "join" operation makes a Cartesian product of the two
            # tables, the resulting table contains as many rows for a report as
            # many annotations belong to it. These have to be joined by report
            # ID and this is the reason of the aggregating MAX() functions.
            #
            # TODO: The creation of this extended table should be produced by
            # a helper function and it could be used as a sub-query in every
            # other query which originally works on "reports" table.

            annotation_keys = list(map(
                lambda x: x[0],
                session.query(ReportAnnotations.key).distinct().all()))

            annotation_cols = OrderedDict()
            for col in annotation_keys:
                annotation_cols[col] = func.max(sqlalchemy.case([(
                    ReportAnnotations.key == col,
                    ReportAnnotations.value)])).label(f"annotation_{col}")

            if report_filter.isUnique:
                # A report annotation filter cannot be set in WHERE clause if
                # we use annotation parameters in aggregate functions to
                # create a pivot table. Instead of filtering report
                # annotations in WHERE clause, we should use HAVING clause
                # only for filtering aggregate functions.
                # TODO: Fixing report annotation filter in every report server
                # endpoint function.
                annotations_backup = report_filter.annotations
                report_filter.annotations = None
                filter_expression, join_tables = process_report_filter(
                    session, run_ids, report_filter, cmp_data)

                sort_types, sort_type_map, order_type_map = \
                    get_sort_map(sort_types, True)

                # TODO: Create a helper function for common section of unique
                # and non unique modes.
                sub_query = session.query(Report,
                                          File.filename,
                                          Checker.analyzer_name,
                                          Checker.checker_name,
                                          Checker.severity,
                                          func.row_number().over(
                                            partition_by=Report.bug_id,
                                            order_by=desc(Report.id)
                                          ).label("row_num"),
                                          *annotation_cols.values()) \
                                   .join(Checker,
                                         Report.checker_id == Checker.id) \
                                   .options(contains_eager(Report.checker)) \
                                   .outerjoin(File,
                                              Report.file_id == File.id) \
                                   .outerjoin(ReportAnnotations,
                                              Report.id ==
                                              ReportAnnotations.report_id)

                sub_query = apply_report_filter(sub_query,
                                                filter_expression,
                                                join_tables,
                                                [File, Checker])

                sub_query = sub_query.group_by(Report.id, File.id, Checker.id)

                if annotations_backup:
                    annotations = defaultdict(list)
                    for annotation in annotations_backup:
                        annotations[annotation.first].append(annotation.second)

                    OR = []
                    for key, values in annotations.items():
                        OR.extend([annotation_cols[key].ilike(conv(v))
                                   for v in values])
                    sub_query = sub_query.having(or_(*OR))

                sub_query = sort_results_query(sub_query,
                                               sort_types,
                                               sort_type_map,
                                               order_type_map)

                sub_query = sub_query.subquery().alias()

                q = session.query(sub_query) \
                           .filter(sub_query.c.row_num == 1) \
                           .limit(limit).offset(offset)

                QueryResult = namedtuple('QueryResult', sub_query.c.keys())
                query_result = [QueryResult(*row) for row in q.all()]

                # Get report details if it is required.
                report_details = {}
                if get_details:
                    report_ids = [r.id for r in query_result]
                    report_details = get_report_details(session, report_ids)

                for row in query_result:
                    annotations = {
                        k: v for k, v in zip(
                            annotation_keys,
                            [getattr(row, 'annotation_testcase', None),
                             getattr(row, 'annotation_timestamp', None)]
                            ) if v is not None}

                    review_data = create_review_data(
                        row.review_status,
                        row.review_status_message,
                        row.review_status_author,
                        row.review_status_date,
                        row.review_status_is_in_source)

                    results.append(
                        ReportData(runId=row.run_id,
                                   bugHash=row.bug_id,
                                   checkedFile=row.filename,
                                   checkerMsg=row.checker_message,
                                   reportId=row.id,
                                   fileId=row.file_id,
                                   line=row.line,
                                   column=row.column,
                                   analyzerName=row.analyzer_name,
                                   checkerId=row.checker_name,
                                   severity=row.severity,
                                   reviewData=review_data,
                                   detectionStatus=detection_status_enum(
                                    row.detection_status),
                                   detectedAt=str(row.detected_at),
                                   fixedAt=str(row.fixed_at),
                                   bugPathLength=row.path_length,
                                   details=report_details.get(row.id),
                                   annotations=annotations))
            else:  # not is_unique
                filter_expression, join_tables = process_report_filter(
                    session, run_ids, report_filter, cmp_data,
                    keep_all_annotations=True)

                sort_types, sort_type_map, order_type_map = \
                    get_sort_map(sort_types)

                q = session.query(Report,
                                  File.filepath,
                                  *annotation_cols.values()) \
                    .join(Checker,
                          Report.checker_id == Checker.id) \
                    .options(contains_eager(Report.checker)) \
                    .outerjoin(File,
                               Report.file_id == File.id) \
                    .outerjoin(
                        ReportAnnotations,
                        Report.id == ReportAnnotations.report_id)

                # Grouping by "reports.id" is described at the beginning of
                # this function. Grouping by "files.id" is necessary, because
                # "files" table is joined for gathering file names belonging to
                # the given report. According to SQL syntax if there is a group
                # by report IDs then files should also be either grouped or an
                # aggregate function must be applied on them. The same applies
                # to the "checkers" table.
                q = q.group_by(Report.id, File.id, Checker.id)

                # The "Checker" entity is eagerly loaded for each "Report" as
                # there is a guaranteed FOREIGN KEY ... NOT NULL relationship
                # to a valid entity. Because of this, letting "join_tables"
                # add "Checker" here is actually ill-formed, as it would
                # result in queries that ambiguously refer to the same table.
                q = apply_report_filter(q, filter_expression, join_tables,
                                        [File, Checker])
                q = sort_results_query(q,
                                       sort_types,
                                       sort_type_map,
                                       order_type_map)

                # Most queries are using paging of reports due their great
                # number. This is implemented by LIMIT and OFFSET in the SQL
                # queries. However, if there is no ordering in the query, then
                # the reports in different pages may overlap. This ordering
                # prevents it.
                q = q.order_by(Report.id)

                if report_filter.annotations is not None:
                    annotations = defaultdict(list)
                    for annotation in report_filter.annotations:
                        annotations[annotation.first].append(annotation.second)

                    OR = []
                    for key, values in annotations.items():
                        OR.extend([annotation_cols[key].ilike(conv(v))
                                   for v in values])
                    q = q.having(or_(*OR))

                q = q.limit(limit).offset(offset)

                query_result = q.all()

                # Get report details if it is required.
                report_details = {}
                if get_details:
                    report_ids = [r[0].id for r in query_result]
                    report_details = get_report_details(session, report_ids)

                for row in query_result:
                    report, filepath = row[0], row[1]
                    annotations = {
                        k: v for k, v in zip(annotation_keys, row[2:])
                        if v is not None}

                    review_data = create_review_data(
                        report.review_status,
                        report.review_status_message,
                        report.review_status_author,
                        report.review_status_date,
                        report.review_status_is_in_source)

                    results.append(
                        ReportData(runId=report.run_id,
                                   bugHash=report.bug_id,
                                   checkedFile=filepath,
                                   checkerMsg=report.checker_message,
                                   reportId=report.id,
                                   fileId=report.file_id,
                                   line=report.line,
                                   column=report.column,
                                   analyzerName=report.checker.analyzer_name,
                                   checkerId=report.checker.checker_name,
                                   severity=report.checker.severity,
                                   reviewData=review_data,
                                   detectionStatus=detection_status_enum(
                                       report.detection_status),
                                   detectedAt=str(report.detected_at),
                                   fixedAt=str(report.fixed_at) if
                                   report.fixed_at else None,
                                   bugPathLength=report.path_length,
                                   details=report_details.get(report.id),
                                   annotations=annotations))

            return results

    @exc_to_thrift_reqfail
    @timeit
    def getReportAnnotations(self, run_ids, report_filter, cmp_data):
        self.__require_view()

        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            extended_table = session.query(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)
                extended_table = extended_table.add_columns(
                    ReportAnnotations.key.label('annotations_key'),
                    ReportAnnotations.value.label('annotations_value')
                ).group_by(ReportAnnotations.key, ReportAnnotations.value)

                extended_table = extended_table.subquery()

                result = session.query(extended_table.c.annotations_value) \
                    .distinct() \
                    .filter(
                        *(extended_table.c.annotations_key == annotation.first
                          for annotation in report_filter.annotations)) \
                    .all()
            else:
                extended_table = extended_table.subquery()

                result = session.query(ReportAnnotations.value) \
                    .distinct() \
                    .join(
                        extended_table,
                        ReportAnnotations.report_id == extended_table.c.id) \
                    .all()

        return list(map(lambda x: x[0], result))

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

            reports_subq = session.query(Report.bug_id, Report.run_id)
            reports_subq = apply_report_filter(
                reports_subq, filter_expression, join_tables)

            if report_filter.annotations is not None:
                reports_subq = reports_subq.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                reports_subq = reports_subq.group_by(Report.id)

            reports_subq = reports_subq.subquery()

            if report_filter is not None and report_filter.isUnique:
                count_col = func.count(reports_subq.c.bug_id.distinct())
            else:
                count_col = func.count(literal_column('*'))

            q = session.query(Run.id, func.max(Run.name), count_col) \
                .select_from(reports_subq) \
                .join(Run, Run.id == reports_subq.c.run_id) \
                .group_by(Run.id) \
                .order_by(Run.name)

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

            if report_filter.isUnique:
                q = session.query(Report.bug_id.distinct())
            else:
                q = session.query(Report.bug_id)

            if report_filter.annotations is not None:
                q = q.outerjoin(ReportAnnotations,
                                ReportAnnotations.report_id == Report.id)
                q = q.group_by(Report.id)

            q = apply_report_filter(q, filter_expression, join_tables)

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
                f'rev_st_changed_msg {old_review_status} ' \
                f'{new_review_status} {shlex.quote(message)}'
        else:
            system_comment_msg = \
                f'rev_st_changed {old_review_status} {new_review_status}'

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
        self.__require_view()

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
        if not sort_mode:
            sort_mode = ReviewStatusRuleSortMode(
                type=ReviewStatusRuleSortType.DATE,
                ord=Order.DESC)

        result = []

        # To avoid modifiying the collection due to chunking
        rule_filter_copy = deepcopy(rule_filter)

        def getRules(reportHashes=None):
            if rule_filter and reportHashes:
                rule_filter_copy.reportHashes = reportHashes
            q = get_rs_rule_query(session, rule_filter_copy, sort_mode)

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

        with DBSession(self._Session) as session:
            if rule_filter and rule_filter.reportHashes:
                # Diffing with a large ammount of report hashes passed in the
                # filter (60K) caused a hanging report diffing.
                # The probable cause of this is the ILIKE matching in the
                # underlying logic. Chunking the request solves this issue.
                for hash_chunk in util.chunks(
                        rule_filter.reportHashes,
                        SQLITE_MAX_VARIABLE_NUMBER):
                    getRules(hash_chunk)
                return result
            else:
                return getRules()

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
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    f'Report id {report_id} was not found in the database.')

    @exc_to_thrift_reqfail
    @timeit
    def getCommentCount(self, report_id):
        """
            Return the number of comments for the given bug.
        """
        self.__require_view()
        with DBSession(self._Session) as session:
            report = session.query(Report).get(report_id)
            commentCount = 0
            if report:
                commentCount = session.query(Comment) \
                    .filter(Comment.bug_hash == report.bug_id) \
                    .count()

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
                msg = f'Report id {report_id} was not found in the database.'
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
                if comment.author not in ('Anonymous', user):
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                        'Unathorized comment modification!')

                # Create system comment if the message is changed.
                message = comment.message.decode('utf-8')
                if message != content:
                    system_comment_msg = \
                        f'comment_changed {shlex.quote(message)} ' \
                        f'{shlex.quote(content)}'

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
                msg = f'Comment id {comment_id} was not found in the database.'
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
                if comment.author not in ('Anonymous', user):
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
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    f'Comment id {comment_id} was not found in the database.')

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerDoc(self, _):
        """
        Parameters:
         - checkerId
        """
        self.__require_view()
        return ""

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerLabels(
        self,
        checkers: List[ttypes.Checker]
    ) -> List[List[str]]:
        """ Return the list of labels to each checker. """
        self.__require_view()

        labels = []
        for checker in checkers:
            analyzer_name = None if not checker.analyzerName \
                else str(checker.analyzerName)
            analyzer_name = analyzer_name \
                if (analyzer_name and analyzer_name.lower() != "unknown") \
                else None

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
                # pylint: disable=raise-missing-from
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    "Failed to get blame information for file id: " + fileId)

    @exc_to_thrift_reqfail
    @timeit
    def getLinesInSourceFileContents(self, lines_in_files_requested, encoding):
        self.__require_view()
        with DBSession(self._Session) as session:
            res = defaultdict(lambda: defaultdict(str))

            # This will contain all the lines for the given fileId
            contents_to_file_id = defaultdict(list)
            # The goal of the chunking is not for achieving better performace
            # but to be compatible with SQLITE dbms with larger report counts,
            # with larger report data.
            for chunk in util.chunks(
                    lines_in_files_requested, SQLITE_MAX_VARIABLE_NUMBER):
                contents = session.query(FileContent.content, File.id) \
                        .join(
                            File,
                            FileContent.content_hash == File.content_hash) \
                        .filter(File.id.in_(
                                [line.fileId if line.fileId is not None
                                    else LOG.warning(
                                        "File content requested "
                                        f"without fileId {line.fileId}")
                                    for line in chunk])) \
                        .all()
                for content in contents:
                    lines = zlib.decompress(
                        content.content).decode('utf-8', 'ignore').split('\n')
                    contents_to_file_id[content.id] = lines

            for files in lines_in_files_requested:
                for line in files.lines:
                    lines = contents_to_file_id[files.fileId]
                    content = '' if len(lines) < line else lines[line - 1]
                    if encoding == Encoding.BASE64:
                        content = convert.to_b64(content)
                    res[files.fileId][line] = content

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

            extended_table = session \
                .query(Report.bug_id,
                       Checker.checker_name,
                       Checker.severity) \
                .join(Checker,
                      Report.checker_id == Checker.id)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables, [Checker])

            extended_table = extended_table.subquery()

            if report_filter.isUnique:
                q = session.query(
                    func.max(extended_table.c.checker_name)
                        .label("checker_name"),
                    func.max(extended_table.c.severity).label("severity"),
                    extended_table.c.bug_id)
            else:
                q = session.query(
                    extended_table.c.checker_name,
                    extended_table.c.severity,
                    func.count(literal_column('*')))

            q = q.select_from(extended_table)

            if report_filter.isUnique:
                q = q.group_by(extended_table.c.bug_id).subquery()
                unique_checker_q = session.query(q.c.checker_name,
                                                 func.max(q.c.severity),
                                                 func.count(q.c.bug_id)) \
                    .group_by(q.c.checker_name) \
                    .order_by(q.c.checker_name)
            else:
                unique_checker_q = q.group_by(extended_table.c.checker_name,
                                              extended_table.c.severity) \
                    .order_by(extended_table.c.checker_name)

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
    def getCheckerStatusVerificationDetails(self, run_ids, report_filter):
        self.__require_view()

        with DBSession(self._Session) as session:
            max_run_histories = session.query(
                RunHistory.run_id,
                func.max(RunHistory.id).label('max_run_history_id'),
            ) \
                .filter(RunHistory.run_id.in_(run_ids) if run_ids else True) \
                .group_by(RunHistory.run_id)

            run_id_expression = get_run_id_expression(session, report_filter)

            subquery = (
                session.query(
                    run_id_expression,
                    Checker.id.label("checker_id"),
                    Checker.checker_name,
                    Checker.analyzer_name,
                    Checker.severity,
                    Report.bug_id,
                    Report.detection_status,
                    Report.review_status,
                )
                .join(RunHistory)
                .join(AnalysisInfo, RunHistory.analysis_info)
                .join(DB_AnalysisInfoChecker, (
                    (AnalysisInfo.id ==
                     DB_AnalysisInfoChecker.analysis_info_id)
                    & (DB_AnalysisInfoChecker.enabled.is_(True))))
                .join(Checker,
                      DB_AnalysisInfoChecker.checker_id == Checker.id)
                .outerjoin(Report, ((Checker.id == Report.checker_id)
                                    & (Run.id == Report.run_id)))
                .filter(RunHistory.id == max_run_histories.subquery()
                        .c.max_run_history_id)
            )

            if report_filter.isUnique:
                subquery = subquery.group_by(
                    Checker.id,
                    Checker.checker_name,
                    Checker.analyzer_name,
                    Checker.severity,
                    Report.bug_id,
                    Report.detection_status,
                    Report.review_status
                )

            subquery = subquery.subquery()

            is_enabled_case = get_is_enabled_case(subquery)
            is_opened_case = get_is_opened_case(subquery)

            query = (
                session.query(
                    subquery.c.checker_id,
                    subquery.c.checker_name,
                    subquery.c.analyzer_name,
                    subquery.c.severity,
                    subquery.c.run_id,
                    is_enabled_case.label("isEnabled"),
                    is_opened_case.label("isOpened"),
                    func.count(subquery.c.bug_id)
                )
                .group_by(
                    subquery.c.checker_id,
                    subquery.c.checker_name,
                    subquery.c.analyzer_name,
                    subquery.c.severity,
                    subquery.c.run_id,
                    is_enabled_case,
                    is_opened_case
                )
            )

            checker_stats = {}
            all_run_id = [runId for runId, _ in max_run_histories.all()]
            for checker_id, \
                checker_name, \
                analyzer_name, \
                severity, \
                run_id_list, \
                is_enabled, \
                is_opened, \
                cnt \
                    in query.all():

                checker_stat = checker_stats.get(
                    checker_id,
                    CheckerStatusVerificationDetail(
                        checkerName=checker_name,
                        analyzerName=analyzer_name,
                        enabled=[],
                        disabled=all_run_id.copy(),
                        severity=severity,
                        closed=0,
                        outstanding=0
                    ))

                if is_enabled:
                    for r in (run_id_list.split(",")
                              if isinstance(run_id_list, str)
                              else [run_id_list]):
                        run_id = int(r)
                        if run_id not in checker_stat.enabled:
                            checker_stat.enabled.append(run_id)
                        if run_id in checker_stat.disabled:
                            checker_stat.disabled.remove(run_id)

                if is_enabled and is_opened:
                    checker_stat.outstanding += cnt
                else:
                    checker_stat.closed += cnt

                checker_stats[checker_id] = checker_stat

            return checker_stats

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

            extended_table = session \
                .query(Checker.analyzer_name,
                       Report.bug_id) \
                .join(Checker,
                      Report.checker_id == Checker.id)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables, [Checker])

            extended_table = extended_table.subquery()

            if report_filter.isUnique:
                q = session.query(func.max(
                    extended_table.c.analyzer_name).label('analyzer_name'),
                    extended_table.c.bug_id)
            else:
                q = session.query(extended_table.c.analyzer_name,
                                  func.count(literal_column('*')))

            q = q.select_from(extended_table)

            if report_filter.isUnique:
                q = q.group_by(extended_table.c.bug_id).subquery()
                analyzer_name_q = session.query(q.c.analyzer_name,
                                                func.count(q.c.bug_id)) \
                    .group_by(q.c.analyzer_name) \
                    .order_by(q.c.analyzer_name)
            else:
                analyzer_name_q = q.group_by(extended_table.c.analyzer_name) \
                    .order_by(extended_table.c.analyzer_name)

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

            extended_table = session \
                .query(Report.bug_id,
                       Checker.severity) \
                .join(Checker,
                      Report.checker_id == Checker.id)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables, [Checker])

            extended_table = extended_table.subquery()

            if report_filter.isUnique:
                q = session.query(
                    func.max(extended_table.c.severity).label("severity"),
                    extended_table.c.bug_id)
            else:
                q = session.query(extended_table.c.severity,
                                  func.count(literal_column('*')))

            q = q.select_from(extended_table)

            if report_filter.isUnique:
                q = q.group_by(extended_table.c.bug_id).subquery()
                severities = session.query(q.c.severity,
                                           func.count(q.c.bug_id)) \
                    .group_by(q.c.severity)
            else:
                severities = q.group_by(extended_table.c.severity)

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

            extended_table = session.query(
                Report.checker_message,
                Report.bug_id)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables)

            extended_table = extended_table.subquery()

            if report_filter.isUnique:
                q = session.query(
                    func.max(extended_table.c.checker_message).label(
                        'checker_message'),
                    extended_table.c.bug_id)
            else:
                q = session.query(extended_table.c.checker_message,
                                  func.count(literal_column('*')))

            q = q.select_from(extended_table)

            if report_filter.isUnique:
                q = q.group_by(extended_table.c.bug_id).subquery()
                checker_messages = session.query(q.c.checker_message,
                                                 func.count(q.c.bug_id)) \
                    .group_by(q.c.checker_message) \
                    .order_by(q.c.checker_message)
            else:
                checker_messages = q \
                    .group_by(extended_table.c.checker_message) \
                    .order_by(extended_table.c.checker_message)

            if limit:
                checker_messages = checker_messages.limit(limit).offset(offset)

            results = dict(checker_messages.all())
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getReportStatusCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_view()
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            extended_table = session.query(
                Report.review_status,
                Report.detection_status,
                Report.bug_id
            )

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id
                )
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables)

            extended_table = extended_table.subquery()

            is_outstanding_case = get_is_opened_case(extended_table)
            case_label = "isOutstanding"

            if report_filter.isUnique:
                q = session.query(
                    is_outstanding_case.label(case_label),
                    func.count(extended_table.c.bug_id.distinct())) \
                    .group_by(is_outstanding_case)
            else:
                q = session.query(
                    is_outstanding_case.label(case_label),
                    func.count(extended_table.c.bug_id)) \
                    .group_by(is_outstanding_case)

            results = {
                report_status_enum(
                    "outstanding" if isOutstanding
                    else "closed"
                ): count for isOutstanding, count in q
            }

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
        with DBSession(self._Session) as session:
            filter_expression, join_tables = process_report_filter(
                session, run_ids, report_filter, cmp_data)

            extended_table = session.query(
                Report.review_status,
                Report.bug_id)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables)

            extended_table = extended_table.subquery()

            if report_filter.isUnique:
                q = session.query(
                    extended_table.c.review_status,
                    func.count(extended_table.c.bug_id.distinct()))
            else:
                q = session.query(
                    extended_table.c.review_status,
                    func.count(extended_table.c.bug_id))

            q = q \
                .select_from(extended_table) \
                .group_by(extended_table.c.review_status)

        return {review_status_enum(rev_status): count
                for rev_status, count in q}

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

            extended_table = session.query(
                Report.file_id,
                Report.bug_id,
                Report.id)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables)

            extended_table = extended_table.subquery()

            count_col = extended_table.c.bug_id.distinct() if \
                report_filter.isUnique else extended_table.c.bug_id

            stmt = session.query(
                    File.filepath,
                    func.count(count_col).label('report_num')) \
                .join(
                    extended_table, File.id == extended_table.c.file_id) \
                .group_by(File.filepath) \
                .order_by(desc('report_num'))

            if limit:
                stmt = stmt.limit(limit).offset(offset)

            for fp, count in stmt:
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

            if report_filter.annotations is not None:
                report_cnt_q = report_cnt_q.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                report_cnt_q = report_cnt_q.group_by(Report.id)

            report_cnt_q = apply_report_filter(
                report_cnt_q, filter_expression, join_tables)
            report_cnt_q = report_cnt_q.filter(
                Report.run_id.in_(tag_run_ids)).subquery()

            count_expr = func.count(
                report_cnt_q.c.bug_id if not report_filter.isUnique
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

            extended_table = session.query(
                Report.detection_status,
                Report.bug_id)

            if report_filter.annotations is not None:
                extended_table = extended_table.outerjoin(
                    ReportAnnotations,
                    ReportAnnotations.report_id == Report.id)
                extended_table = extended_table.group_by(Report.id)

            extended_table = apply_report_filter(
                extended_table, filter_expression, join_tables)

            extended_table = extended_table.subquery()

            if report_filter.isUnique:
                q = session.query(
                    extended_table.c.detection_status,
                    func.count(extended_table.c.bug_id.distinct()))
            else:
                q = session.query(
                    extended_table.c.detection_status,
                    func.count(literal_column('*')))

            q = q \
                .select_from(extended_table) \
                .group_by(extended_table.c.detection_status)

            results = {
                detection_status_enum(k): v for k,
                v in q}

        return results

    @exc_to_thrift_reqfail
    @timeit
    def getFailedFilesCount(self, run_ids):
        """
        Count the number of uniqued failed files in the latest storage of each
        given run. If the run id list is empty the number of failed files will
        be counted for all of the runs.
        """
        self.__require_view()

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
        self.__require_view()

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

                if report_filter.annotations is not None:
                    q = q.outerjoin(ReportAnnotations,
                                    ReportAnnotations.report_id == Report.id)
                    q = q.group_by(Report.id)

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
        db_cleanup.remove_unused_comments(self._product)
        db_cleanup.remove_unused_analysis_info(self._product)

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
            runs = []
            deleted_run_cnt = 0

            for run in q.all():
                try:
                    runs.append(run.name)
                    session.delete(run)
                    session.commit()
                    deleted_run_cnt += 1
                except Exception as e:
                    # TODO: Display alert on the GUI if there's an exception
                    # TODO: Catch SQLAlchemyError instead of generic
                    #  exception once it is confirmed that the exception is
                    #  due to a large run deletion timeout based on server
                    #  log warnings
                    # This exception is handled silently because it is
                    # expected to never occur, but there have been some rare
                    # cases where it occurred due to underlying reasons.
                    # Handling it silently ensures that the Number of runs
                    # counter is not affected by the exception.
                    LOG.warning(f"Suppressed an exception while "
                                f"deleting run {run.name}. Error: {e}")

            session.close()

            LOG.info("Runs '%s' were removed by '%s'.", "', '".join(runs),
                     self._get_username())

        # Decrement the number of runs but do not update the latest storage
        # date.
        self._set_run_data_for_curr_product(-1 * deleted_run_cnt)

        # Remove unused comments and unused analysis info from the database.
        # Originally db_cleanup.remove_unused_data() was used here which
        # removes unused file entries tool. However removing files at the same
        # time with a storage concurrently results foreign key constraint
        # error. An alternative solution can be adding a timestamp to file
        # entries to delay their removal. The same comment applies to
        # removeRunReports() function.
        db_cleanup.remove_unused_comments(self._product)
        db_cleanup.remove_unused_analysis_info(self._product)

        return bool(runs)

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
                msg = f'Run id {run_id} was not found in the database.'
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
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    f'Source component {name} was not found in the database.')

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
                        set(fc.content_hash for fc in q))

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
                        set(fc.content_hash for fc in q))

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

        return bool(self._manager.get_analysis_statistics_dir())

    @exc_to_thrift_reqfail
    @timeit
    def getAnalysisStatisticsLimits(self):
        self.__require_store()

        cfg = {}

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

            for anal_stat, _ in query:
                failed_files = zlib.decompress(anal_stat.failed_files).decode(
                    'utf-8').split('\n') if anal_stat.failed_files else []
                analyzer_version = zlib.decompress(
                    anal_stat.version).decode('utf-8') \
                    if anal_stat.version else None

                analyzer_statistics[anal_stat.analyzer_type] = \
                    ttypes.AnalyzerStatistics(version=analyzer_version,
                                              failed=anal_stat.failed,
                                              failedFilePaths=failed_files,
                                              successful=anal_stat.successful)
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
