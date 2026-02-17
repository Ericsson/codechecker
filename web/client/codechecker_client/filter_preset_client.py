# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd filterPreset' subcommands.
"""

import argparse
import json
import sys
from datetime import datetime
from codechecker_report_converter import twodim

from codechecker_common import logger
from codechecker_web.shared.env import get_user_input
from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from .client import setup_client
from .cmd_line import CmdLineOutputEncoder

LOG = None

def init_logger(level, stream=None, logger_name='system'):
    logger.setup_logger(level, stream)
    global LOG
    LOG = logger.get_logger(logger_name)


def build_filter_config_from_args(args):
    """
    Build a ReportFilter object from command-line arguments.
    Returns the ReportFilter object directly.
    """
    args_dict = vars(args)

    def get_arg(key, default=None):
        value = args_dict.get(key, default)
        if value == argparse.SUPPRESS:
            return default
        return value

    def convert_severity(severity_list):
        """Convert severity strings to integer enum values using ttypes"""
        if not severity_list:
            return None
        try:
            return [ttypes.Severity._NAMES_TO_VALUES[s.upper()]
                    for s in severity_list]
        except KeyError as e:
            invalid_value = str(e).strip("'")
            valid_values = ', '.join(ttypes.Severity._NAMES_TO_VALUES.keys()).lower()
            LOG.error("Invalid severity value: %s", invalid_value.lower())
            LOG.error("Valid values are: %s", valid_values)
            sys.exit(1)

    def convert_review_status(status_list):
        """Convert review status strings to integer enum values using ttypes"""
        if not status_list:
            return None
        try:
            return [ttypes.ReviewStatus._NAMES_TO_VALUES[s.upper()]
                    for s in status_list]
        except KeyError as e:
            invalid_value = str(e).strip("'")
            valid_values = ', '.join(ttypes.ReviewStatus._NAMES_TO_VALUES.keys()).lower()
            LOG.error("Invalid review status value: %s", invalid_value.lower())
            LOG.error("Valid values are: %s", valid_values)
            sys.exit(1)

    def convert_detection_status(status_list):
        """Convert detection status strings to integer enum values using ttypes"""
        if not status_list:
            return None
        try:
            return [ttypes.DetectionStatus._NAMES_TO_VALUES[s.upper()]
                    for s in status_list]
        except KeyError as e:
            invalid_value = str(e).strip("'")
            valid_values = ', '.join(ttypes.DetectionStatus._NAMES_TO_VALUES.keys()).lower()
            LOG.error("Invalid detection status value: %s", invalid_value.lower())
            LOG.error("Valid values are: %s", valid_values)
            sys.exit(1)

    def convert_report_status(status_list):
        """Convert report status strings to integer enum values using ttypes"""
        if not status_list:
            return None
        try:
            return [ttypes.ReportStatus._NAMES_TO_VALUES[s.upper()]
                    for s in status_list]
        except KeyError as e:
            invalid_value = str(e).strip("'")
            valid_values = ', '.join(ttypes.ReportStatus._NAMES_TO_VALUES.keys()).lower()
            LOG.error("Invalid report status value: %s", invalid_value.lower())
            LOG.error("Valid values are: %s", valid_values)
            sys.exit(1)

    # 1. BugPathLength - parse "min:max" format
    recreated_bug_path_length = None
    bug_path_str = get_arg('bug_path_length')
    if bug_path_str:
        if ':' in bug_path_str:
            parts = bug_path_str.split(':')
            min_val = int(parts[0]) if parts[0] else None
            max_val = int(parts[1]) if len(parts) > 1 and parts[1] else None
            recreated_bug_path_length = ttypes.BugPathLengthRange(
                min=min_val,
                max=max_val
            )

    # 2. ReportDate - construct from detected_* and fixed_* arguments
    recreated_date = None
    detected_after = get_arg('detected_after')
    detected_before = get_arg('detected_before')
    fixed_after = get_arg('fixed_after')
    fixed_before = get_arg('fixed_before')

    detected_interval = None
    if detected_after or detected_before:
        detected_interval = ttypes.DateInterval(
            before=int(detected_before.timestamp()) if detected_before else None,
            after=int(detected_after.timestamp()) if detected_after else None
        )

    fixed_interval = None
    if fixed_after or fixed_before:
        fixed_interval = ttypes.DateInterval(
            before=int(fixed_before.timestamp()) if fixed_before else None,
            after=int(fixed_after.timestamp()) if fixed_after else None
        )

    if detected_interval or fixed_interval:
        recreated_date = ttypes.ReportDate(
            detected=detected_interval,
            fixed=fixed_interval
        )

    # 3. Timestamps - convert datetime objects to Unix timestamps
    open_reports_date = get_arg('open_reports_date')
    open_reports_timestamp = int(open_reports_date.timestamp()) if open_reports_date else None

    detected_at = get_arg('detected_at')
    first_detection_timestamp = int(detected_at.timestamp()) if detected_at else None

    fixed_at = get_arg('fixed_at')
    fix_date_timestamp = int(fixed_at.timestamp()) if fixed_at else None

    # 4. Create and return the ReportFilter object
    return ttypes.ReportFilter(
        filepath=get_arg('file_path'),
        checkerMsg=get_arg('checker_msg'),
        checkerName=get_arg('checker_name'),
        reportHash=get_arg('report_hash'),
        severity=convert_severity(get_arg('severity')),
        reviewStatus=convert_review_status(get_arg('review_status')),
        detectionStatus=convert_detection_status(get_arg('detection_status')),
        runHistoryTag=get_arg('tag'),
        firstDetectionDate=first_detection_timestamp,
        fixDate=fix_date_timestamp,
        isUnique=get_arg('uniqueing') == 'on' if get_arg('uniqueing') else None,
        runName=None,
        runTag=None,
        componentNames=get_arg('component'),
        bugPathLength=recreated_bug_path_length,
        date=recreated_date,
        analyzerNames=get_arg('analyzer_name'),
        openReportsDate=open_reports_timestamp,
        cleanupPlanNames=None,
        fileMatchesAnyPoint=get_arg('anywhere_on_report_path'),
        componentMatchesAnyPoint=get_arg('single_origin_report'),
        annotations=None,
        reportStatus=convert_report_status(get_arg('report_status')),
    )

def display_preset_details(preset):
    """Display the complete preset information including ID."""

    print("\nFilter Preset Created/Updated:")
    print("=" * 60)
    print(f"ID:          {preset.id}")
    print(f"Name:        {preset.name}")

    print("\nFilter Configuration:")
    if preset.reportFilter:
        rf = preset.reportFilter

        if rf.filepath:
            print(f"  File paths: {', '.join(rf.filepath)}")

        if rf.checkerName:
            print(f"  Checker names: {', '.join(rf.checkerName)}")

        if rf.checkerMsg:
            print(f"  Checker messages: {', '.join(rf.checkerMsg)}")

        if rf.reportHash:
            print(f"  Report hashes: {', '.join(rf.reportHash)}")

        if rf.severity:
            severity_names = [ttypes.Severity._VALUES_TO_NAMES.get(s, str(s))
                            for s in rf.severity]
            print(f"  Severity: {', '.join(severity_names)}")

        if rf.reviewStatus:
            review_names = [ttypes.ReviewStatus._VALUES_TO_NAMES.get(s, str(s))
                          for s in rf.reviewStatus]
            print(f"  Review status: {', '.join(review_names)}")

        if rf.detectionStatus:
            detection_names = [ttypes.DetectionStatus._VALUES_TO_NAMES.get(s, str(s))
                             for s in rf.detectionStatus]
            print(f"  Detection status: {', '.join(detection_names)}")

        if rf.runHistoryTag:
            print(f"  Tags: {', '.join(rf.runHistoryTag)}")

        if rf.componentNames:
            print(f"  Components: {', '.join(rf.componentNames)}")

        if rf.analyzerNames:
            print(f"  Analyzer names: {', '.join(rf.analyzerNames)}")

        if rf.bugPathLength:
            min_val = rf.bugPathLength.min if rf.bugPathLength.min is not None else "any"
            max_val = rf.bugPathLength.max if rf.bugPathLength.max is not None else "any"
            print(f"  Bug path length: {min_val}:{max_val}")

        if rf.isUnique is not None:
            print(f"  Is unique: {'yes' if rf.isUnique else 'no'}")

        if rf.firstDetectionDate:
            date_str = datetime.fromtimestamp(rf.firstDetectionDate).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  First detection date: {date_str}")

        if rf.fixDate:
            date_str = datetime.fromtimestamp(rf.fixDate).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  Fix date: {date_str}")

        if rf.openReportsDate:
            date_str = datetime.fromtimestamp(rf.openReportsDate).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  Open reports date: {date_str}")

        if rf.date:
            if rf.date.detected:
                print(f"  Detected date range:")
                if rf.date.detected.after:
                    print(f"    After: {datetime.fromtimestamp(rf.date.detected.after).strftime('%Y-%m-%d')}")
                if rf.date.detected.before:
                    print(f"    Before: {datetime.fromtimestamp(rf.date.detected.before).strftime('%Y-%m-%d')}")
            if rf.date.fixed:
                print(f"  Fixed date range:")
                if rf.date.fixed.after:
                    print(f"    After: {datetime.fromtimestamp(rf.date.fixed.after).strftime('%Y-%m-%d')}")
                if rf.date.fixed.before:
                    print(f"    Before: {datetime.fromtimestamp(rf.date.fixed.before).strftime('%Y-%m-%d')}")

        if rf.fileMatchesAnyPoint:
            print(f"  File matches any point: yes")

        if rf.componentMatchesAnyPoint:
            print(f"  Component matches any point: yes")

        if not any([rf.filepath, rf.checkerName, rf.checkerMsg, rf.reportHash,
                    rf.severity, rf.reviewStatus, rf.detectionStatus, rf.runHistoryTag,
                    rf.componentNames, rf.analyzerNames, rf.bugPathLength,
                    rf.firstDetectionDate, rf.fixDate, rf.openReportsDate, rf.date]):
            print("  (no filters configured)")
    else:
        print("  (no filters configured)")

    print("=" * 60)


def summarize_filters(report_filter):
    """Create a summary string of active filters for display."""
    if not report_filter:
        return '(none)'

    active = []
    rf = report_filter

    if rf.filepath:
        active.append(f"filepath({len(rf.filepath)})")
    if rf.checkerName:
        active.append(f"checkerName({len(rf.checkerName)})")
    if rf.checkerMsg:
        active.append(f"checkerMsg({len(rf.checkerMsg)})")
    if rf.reportHash:
        active.append(f"reportHash({len(rf.reportHash)})")
    if rf.severity:
        active.append(f"severity({len(rf.severity)})")
    if rf.reviewStatus:
        active.append(f"reviewStatus({len(rf.reviewStatus)})")
    if rf.detectionStatus:
        active.append(f"detectionStatus({len(rf.detectionStatus)})")
    if rf.runHistoryTag:
        active.append(f"tag({len(rf.runHistoryTag)})")
    if rf.componentNames:
        active.append(f"components({len(rf.componentNames)})")
    if rf.analyzerNames:
        active.append(f"analyzers({len(rf.analyzerNames)})")
    if rf.bugPathLength:
        active.append("bugPathLength")
    if rf.date:
        active.append("dateRange")
    if rf.isUnique is not None:
        active.append("uniqueing")

    return ', '.join(active) if active else '(none)'

def handle_new_preset(args):
    """Handler for creating or editing a filter preset."""
    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    report_filter = build_filter_config_from_args(args)

    PresetFilter = ttypes.FilterPreset(
        None,  # ID assigned by server (or existing ID if updating)
        args.preset_name,
        report_filter
    )

    # Check if preset already exists
    existing_presets = client.listFilterPreset()
    list_of_existing_names = [preset.name for preset in existing_presets]
    flag_for_existing = args.preset_name in list_of_existing_names

    if flag_for_existing:
        LOG.info("Filter preset '%s' already exists. Editing...", args.preset_name)
        if not args.force:
            question = 'Do you want to update the existing preset? Y(es)/n(o) '
            if not get_user_input(question):
                LOG.info("No changes made to filter preset.")
                sys.exit(0)

    preset_id = client.storeFilterPreset(PresetFilter)

    if preset_id != -1:
        action = "updated" if flag_for_existing else "created"
        LOG.info("Filter preset '%s' %s successfully.", args.preset_name, action)

        stored_preset = client.getFilterPreset(preset_id)

        if stored_preset:
            display_preset_details(stored_preset)
        else:
            # This should never happen, but handle gracefully
            LOG.warning("Preset was saved but could not be retrieved.")
            LOG.info("Preset ID: %d, Name: %s", preset_id, args.preset_name)
    else:
        LOG.error("An error occurred when saving filter preset.")
        sys.exit(1)

def handle_list_presets(args):
    """Handler for listing all filter presets."""
    # If the given output format is not 'table', redirect logger's output to stderr
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

    client = setup_client(args.product_url)

    # Get all presets
    presets = client.listFilterPreset()

    if not presets:
        LOG.info("No filter presets found.")
        return

    if args.output_format == 'json':
        # For JSON output, include full details with human-readable enum values
        output = []
        for preset in presets:
            rf = preset.reportFilter
            filter_dict = {}

            # Add non-empty fields to filter_dict - using ttypes enums
            if rf.filepath:
                filter_dict['filepath'] = rf.filepath
            if rf.checkerName:
                filter_dict['checkerName'] = rf.checkerName
            if rf.checkerMsg:
                filter_dict['checkerMsg'] = rf.checkerMsg
            if rf.reportHash:
                filter_dict['reportHash'] = rf.reportHash
            if rf.severity:
                filter_dict['severity'] = [ttypes.Severity._VALUES_TO_NAMES.get(s, s)
                                          for s in rf.severity]
            if rf.reviewStatus:
                filter_dict['reviewStatus'] = [ttypes.ReviewStatus._VALUES_TO_NAMES.get(s, s)
                                              for s in rf.reviewStatus]
            if rf.detectionStatus:
                filter_dict['detectionStatus'] = [ttypes.DetectionStatus._VALUES_TO_NAMES.get(s, s)
                                                 for s in rf.detectionStatus]
            if rf.runHistoryTag:
                filter_dict['runHistoryTag'] = rf.runHistoryTag
            if rf.componentNames:
                filter_dict['componentNames'] = rf.componentNames
            if rf.analyzerNames:
                filter_dict['analyzerNames'] = rf.analyzerNames
            if rf.bugPathLength:
                filter_dict['bugPathLength'] = {
                    'min': rf.bugPathLength.min,
                    'max': rf.bugPathLength.max
                }
            if rf.isUnique is not None:
                filter_dict['isUnique'] = rf.isUnique
            if rf.firstDetectionDate:
                filter_dict['firstDetectionDate'] = rf.firstDetectionDate
            if rf.fixDate:
                filter_dict['fixDate'] = rf.fixDate
            if rf.openReportsDate:
                filter_dict['openReportsDate'] = rf.openReportsDate
            if rf.date:
                date_dict = {}
                if rf.date.detected:
                    date_dict['detected'] = {
                        'before': rf.date.detected.before,
                        'after': rf.date.detected.after
                    }
                if rf.date.fixed:
                    date_dict['fixed'] = {
                        'before': rf.date.fixed.before,
                        'after': rf.date.fixed.after
                    }
                filter_dict['dateRange'] = date_dict
            if rf.fileMatchesAnyPoint:
                filter_dict['fileMatchesAnyPoint'] = rf.fileMatchesAnyPoint
            if rf.componentMatchesAnyPoint:
                filter_dict['componentMatchesAnyPoint'] = rf.componentMatchesAnyPoint

            preset_dict = {
                'id': preset.id,
                'name': preset.name,
                'filters': filter_dict
            }
            output.append(preset_dict)

        print(json.dumps(output, indent=2))
    else:  # plaintext, csv, table
        header = ['ID', 'Name', 'Active Filters']
        rows = []
        for preset in presets:
            filter_summary = summarize_filters(preset.reportFilter)

            rows.append((
                str(preset.id),
                preset.name,
                filter_summary
            ))

        print(twodim.to_str(args.output_format, header, rows))

def handle_delete_preset(args):
    """Handler for deleting a filter preset by its ID."""
    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    all_presets = client.listFilterPreset()
    preset = next((p for p in all_presets if p.id == args.preset_id), None)

    if not preset:
        LOG.error("Filter preset with ID %d does not exist!", args.preset_id)
        sys.exit(1)

    if not args.force:
        question = f"Are you sure you want to delete preset '{preset.name}' (ID: {args.preset_id})? Y(es)/n(o) "
        if not get_user_input(question):
            LOG.info("Filter preset was not deleted.")
            sys.exit(0)

    success = client.deleteFilterPreset(args.preset_id)

    if success:
        LOG.info("Filter preset '%s' (ID: %d) successfully deleted.", preset.name, args.preset_id)
    else:
        LOG.error("An error occurred when deleting the filter preset.")
        sys.exit(1)
