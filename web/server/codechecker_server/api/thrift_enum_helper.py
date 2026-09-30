# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Thrift enum helper.
"""


from codechecker_api.python.DBAccess_v6.ttypes import DetectionStatus, \
        ExtendedReportDataType, ReportStatus, ReviewStatus
from codechecker_api.python.ProductManagement_v6.ttypes import Confidentiality


def detection_status_enum(status: str | None) -> DetectionStatus | None:
    if status is None:
        return None
    elif status == 'new':
        return DetectionStatus.NEW
    elif status == 'resolved':
        return DetectionStatus.RESOLVED
    elif status == 'unresolved':
        return DetectionStatus.UNRESOLVED
    elif status == 'reopened':
        return DetectionStatus.REOPENED
    elif status == 'off':
        return DetectionStatus.OFF
    elif status == 'unavailable':
        return DetectionStatus.UNAVAILABLE

    assert False, f"Unknown detection status: {status}"


def detection_status_str(status: DetectionStatus | None) -> str | None:
    if status is None:
        return None
    elif status == DetectionStatus.NEW:
        return 'new'
    elif status == DetectionStatus.RESOLVED:
        return 'resolved'
    elif status == DetectionStatus.UNRESOLVED:
        return 'unresolved'
    elif status == DetectionStatus.REOPENED:
        return 'reopened'
    elif status == DetectionStatus.OFF:
        return 'off'
    elif status == DetectionStatus.UNAVAILABLE:
        return 'unavailable'

    assert False, f"Unknown review status: {status}"


def confidentiality_enum(
    confidentiality: str | None
) -> Confidentiality | None:
    """
    Converts the given string to confidentiality Thrift enum value.
    """
    if confidentiality is None:
        return None
    elif confidentiality == 'CONFIDENTIAL':
        return Confidentiality.CONFIDENTIAL
    elif confidentiality == 'INTERNAL':
        return Confidentiality.INTERNAL
    elif confidentiality == 'OPEN':
        return Confidentiality.OPEN

    assert False, f"Unknown confidentiality: {confidentiality}"


def confidentiality_str(
    confidentiality: Confidentiality | None
) -> str | None:
    """
    Converts the given confidentiality to string.
    """
    if confidentiality is None:
        return None
    elif confidentiality == Confidentiality.CONFIDENTIAL:
        return 'CONFIDENTIAL'
    elif confidentiality == Confidentiality.INTERNAL:
        return 'INTERNAL'
    elif confidentiality == Confidentiality.OPEN:
        return 'OPEN'

    assert False, f"Unknown confidentiality: {confidentiality}"


def review_status_str(status: ReviewStatus | None) -> str | None:
    """
    Returns the given review status Thrift enum value.
    """
    if status is None:
        return None
    elif status == ReviewStatus.UNREVIEWED:
        return 'unreviewed'
    elif status == ReviewStatus.CONFIRMED:
        return 'confirmed'
    elif status == ReviewStatus.FALSE_POSITIVE:
        return 'false_positive'
    elif status == ReviewStatus.INTENTIONAL:
        return 'intentional'

    assert False, f"Unknown review status: {status}"


def review_status_enum(status: str | None) -> ReviewStatus | None:
    """
    Converts the given review status to string.
    """
    if status is None:
        return None
    elif status == 'unreviewed':
        return ReviewStatus.UNREVIEWED
    elif status == 'confirmed':
        return ReviewStatus.CONFIRMED
    elif status == 'false_positive':
        return ReviewStatus.FALSE_POSITIVE
    elif status == 'intentional':
        return ReviewStatus.INTENTIONAL

    assert False, f"Unknown review status: {status}"


def report_extended_data_type_str(
    status: ExtendedReportDataType | None
) -> str | None:
    """
    Converts the given extended data type to string.
    """
    if status is None:
        return None
    elif status == ExtendedReportDataType.NOTE:
        return 'note'
    elif status == ExtendedReportDataType.MACRO:
        return 'macro'
    elif status == ExtendedReportDataType.FIXIT:
        return 'fixit'

    assert False, f"Unknown ExtendedReportDataType: {status}"


def report_extended_data_type_enum(
    status: str | None
) -> ExtendedReportDataType | None:
    """
    Returns the given extended report data Thrift enum value.
    """
    if status is None:
        return None
    elif status == 'note':
        return ExtendedReportDataType.NOTE
    elif status == 'macro':
        return ExtendedReportDataType.MACRO
    elif status == 'fixit':
        return ExtendedReportDataType.FIXIT

    assert False, f"Unknown ExtendedReportDataType: {status}"


def report_status_str(status: ReportStatus | None) -> str | None:
    """
    Returns the given report status Thrift enum value.
    """
    if status is None:
        return None
    elif status == ReportStatus.OUTSTANDING:
        return 'outstanding'
    elif status == ReportStatus.CLOSED:
        return 'closed'

    assert False, f"Unknown report status: {status}"


def report_status_enum(status: str | None) -> ReportStatus | None:
    """
    Converts the given report status to string.
    """
    if status is None:
        return None
    elif status == 'outstanding':
        return ReportStatus.OUTSTANDING
    elif status == 'closed':
        return ReportStatus.CLOSED

    assert False, f"Unknown report status: {status}"
