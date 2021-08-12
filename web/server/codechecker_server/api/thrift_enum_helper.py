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


from codechecker_api.codeCheckerDBAccess_v6.ttypes import DetectionStatus, \
        ExtendedReportDataType, ReviewStatus
from codechecker_api.ProductManagement_v6.ttypes import Confidentiality


def detection_status_enum(status):
    if status == 'new':
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


def detection_status_str(status):
    if status == DetectionStatus.NEW:
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


def confidentiality_enum(confidentiality: str) -> Confidentiality:
    """
    Converts the given string to confidentiality Thrift enum value.
    """
    if confidentiality == 'CONFIDENTIAL':
        return Confidentiality.CONFIDENTIAL
    elif confidentiality == 'INTERNAL':
        return Confidentiality.INTERNAL
    elif confidentiality == 'OPEN':
        return Confidentiality.OPEN


def confidentiality_str(confidentiality: Confidentiality) -> str:
    """
    Converts the given confidentiality to string.
    """
    if confidentiality == Confidentiality.CONFIDENTIAL:
        return 'CONFIDENTIAL'
    elif confidentiality == Confidentiality.INTERNAL:
        return 'INTERNAL'
    elif confidentiality == Confidentiality.OPEN:
        return 'OPEN'


def review_status_str(status):
    """
    Returns the given review status Thrift enum value.
    """
    if status == ReviewStatus.UNREVIEWED:
        return 'unreviewed'
    elif status == ReviewStatus.CONFIRMED:
        return 'confirmed'
    elif status == ReviewStatus.FALSE_POSITIVE:
        return 'false_positive'
    elif status == ReviewStatus.INTENTIONAL:
        return 'intentional'


def review_status_enum(status):
    """
    Converts the given review status to string.
    """
    if status == 'unreviewed':
        return ReviewStatus.UNREVIEWED
    elif status == 'confirmed':
        return ReviewStatus.CONFIRMED
    elif status == 'false_positive':
        return ReviewStatus.FALSE_POSITIVE
    elif status == 'intentional':
        return ReviewStatus.INTENTIONAL


def report_extended_data_type_str(status):
    """
    Converts the given extended data type to string.
    """
    if status == ExtendedReportDataType.NOTE:
        return 'note'
    elif status == ExtendedReportDataType.MACRO:
        return 'macro'
    elif status == ExtendedReportDataType.FIXIT:
        return 'fixit'


def report_extended_data_type_enum(status):
    """
    Returns the given extended report data Thrift enum value.
    """
    if status == 'note':
        return ExtendedReportDataType.NOTE
    elif status == 'macro':
        return ExtendedReportDataType.MACRO
    elif status == 'fixit':
        return ExtendedReportDataType.FIXIT
