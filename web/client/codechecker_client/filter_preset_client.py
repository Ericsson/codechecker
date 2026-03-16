# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Argument handlers for the 'CodeChecker cmd filter-preset' subcommands.
"""

import json
import sys
from datetime import datetime
from codechecker_report_converter import twodim

from codechecker_common import logger
from codechecker_common.util import thrift_to_json
from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from .client import setup_client
from .cmd_line_client import parse_report_filter_offline

LOG = None


def init_logger(level, stream=None, logger_name='system'):
    logger.setup_logger(level, stream)
    global LOG
    LOG = logger.get_logger(logger_name)


def display_preset_details(preset):
    """
    Display the complete preset information including ID.
    """

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
            severity_names = [
                ttypes.Severity._VALUES_TO_NAMES.get(s, str(s))
                for s in rf.severity
            ]
            print(f"  Severity: {', '.join(severity_names)}")

        if rf.reviewStatus:
            review_names = [
                ttypes.ReviewStatus._VALUES_TO_NAMES.get(s, str(s))
                for s in rf.reviewStatus
            ]
            print(f"  Review status: {', '.join(review_names)}")

        if rf.detectionStatus:
            detection_names = [
                ttypes.DetectionStatus._VALUES_TO_NAMES.get(s, str(s))
                for s in rf.detectionStatus
            ]
            print(f"  Detection status: {', '.join(detection_names)}")

        if rf.runHistoryTag:
            print(f"  Tags: {', '.join(rf.runHistoryTag)}")

        if rf.componentNames:
            print(f"  Components: {', '.join(rf.componentNames)}")

        if rf.analyzerNames:
            print(f"  Analyzer names: {', '.join(rf.analyzerNames)}")

        if rf.bugPathLength:
            min_val = (
                rf.bugPathLength.min
                if rf.bugPathLength.min is not None
                else "any")
            max_val = (
                rf.bugPathLength.max
                if rf.bugPathLength.max is not None
                else "any")
            print(f"  Bug path length: {min_val}:{max_val}")

        if rf.isUnique is not None:
            print(f"  Is unique: {'yes' if rf.isUnique else 'no'}")

        if rf.openReportsDate:
            date_str = datetime.fromtimestamp(
                rf.openReportsDate).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  Open reports date: {date_str}")

        def _fmt(ts):
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

        if rf.date:
            if rf.date.detected:
                print("  Detected date range:")
                if rf.date.detected.after:
                    print(f"    After: {_fmt(rf.date.detected.after)}")
                if rf.date.detected.before:
                    print(f"    Before: {_fmt(rf.date.detected.before)}")

            if rf.date.fixed:
                print("  Fixed date range:")
                if rf.date.fixed.after:
                    print(f"    After: {_fmt(rf.date.fixed.after)}")
                if rf.date.fixed.before:
                    print(f"    Before: {_fmt(rf.date.fixed.before)}")

        if rf.runName:
            print(f"  Run names: {', '.join(rf.runName)}")

        if rf.runTag:
            print(f"  Run tags: {', '.join(str(t) for t in rf.runTag)}")

        if rf.cleanupPlanNames:
            print(f"  Cleanup plans: {', '.join(rf.cleanupPlanNames)}")

        if rf.fileMatchesAnyPoint:
            print("  File matches any point: yes")

        if rf.componentMatchesAnyPoint:
            print("  Component matches any point: yes")

        if rf.annotations:
            for ann in rf.annotations:
                print(f"  Annotation: {ann.first}={ann.second}")

        if rf.reportStatus:
            status_names = [
                ttypes.ReportStatus._VALUES_TO_NAMES.get(s, str(s))
                for s in rf.reportStatus
            ]
            print(f"  Report status: {', '.join(status_names)}")

        if rf.fullReportPathInComponent:
            print("  Full report path in component: yes")

        if not any([rf.filepath, rf.checkerName, rf.checkerMsg,
                    rf.reportHash, rf.severity, rf.reviewStatus,
                    rf.detectionStatus, rf.runHistoryTag,
                    rf.componentNames, rf.analyzerNames,
                    rf.bugPathLength,
                    rf.openReportsDate, rf.date,
                    rf.runName, rf.runTag, rf.cleanupPlanNames,
                    rf.fileMatchesAnyPoint, rf.componentMatchesAnyPoint,
                    rf.annotations, rf.reportStatus,
                    rf.fullReportPathInComponent]):
            print("  (no filters configured)")
    else:
        print("  (no filters configured)")

    print("=" * 60)


def summarize_filters(report_filter):
    """
    Create a summary string of active filters for display.
    """

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
    if rf.runName:
        active.append(f"runName({len(rf.runName)})")
    if rf.runTag:
        active.append(f"runTag({len(rf.runTag)})")
    if rf.openReportsDate:
        active.append("openReportsDate")
    if rf.cleanupPlanNames:
        active.append(f"cleanupPlans({len(rf.cleanupPlanNames)})")
    if rf.fileMatchesAnyPoint:
        active.append("fileMatchesAnyPoint")
    if rf.componentMatchesAnyPoint:
        active.append("componentMatchesAnyPoint")
    if rf.annotations:
        active.append(f"annotations({len(rf.annotations)})")
    if rf.reportStatus:
        active.append(f"reportStatus({len(rf.reportStatus)})")
    if rf.fullReportPathInComponent:
        active.append("fullReportPathInComponent")

    return ', '.join(active) if active else '(none)'


def handle_new_preset(args):
    """
    Handler for creating or editing a filter preset.
    """

    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    report_filter = parse_report_filter_offline(args)

    # Check if preset already exists
    existing_presets = client.listFilterPreset()
    existing_preset = next(
        (p for p in existing_presets if p.name == args.preset_name), None)

    if existing_preset:
        LOG.error(
            "Filter preset '%s' already exists. "
            "Use a different name or delete the "
            "existing preset to create a new one.",
            args.preset_name)

        sys.exit(1)
    else:
        # -1 tells the server to create a new preset
        preset_id_to_send = -1

    preset_filter = ttypes.FilterPreset(
        preset_id_to_send,
        args.preset_name,
        report_filter
    )
    try:
        preset_id = client.storeFilterPreset(preset_filter)

        LOG.info("Filter preset '%s' saved with ID: %d",
                 args.preset_name, preset_id)

        action = "updated" if existing_preset else "created"
        LOG.info(
            f"Filter preset '{args.preset_name}' {action} successfully.")

        stored_preset = client.getFilterPreset(preset_id)

        if stored_preset:
            display_preset_details(stored_preset)
        else:
            # This should never happen, but handle gracefully
            LOG.warning("Preset was saved but could not be retrieved.")
            LOG.info(f"Preset ID: {preset_id}, Name: {args.preset_name}")
    except Exception as e:
        LOG.error("An error occurred while saving the filter preset: %s", e)
        sys.exit(1)


def handle_list_presets(args):
    """
    Handler for listing all filter presets.
    """

    # If the given output format is not 'table',
    # redirect logger's output to stderr
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
        _enum_maps = {
            'severity': ttypes.Severity._VALUES_TO_NAMES,
            'reviewStatus': ttypes.ReviewStatus._VALUES_TO_NAMES,
            'detectionStatus': ttypes.DetectionStatus._VALUES_TO_NAMES,
            'reportStatus': ttypes.ReportStatus._VALUES_TO_NAMES,
        }

        output = []
        for preset in presets:
            filter_dict = thrift_to_json(preset.reportFilter) or {}

            for key, names in _enum_maps.items():
                if key in filter_dict and isinstance(
                        filter_dict[key], list):
                    filter_dict[key] = [
                        names.get(v, v) for v in filter_dict[key]]

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
    """
    Handler for deleting a filter preset by its ID.
    """

    init_logger(args.verbose if 'verbose' in args else None)

    client = setup_client(args.product_url)

    all_presets = client.listFilterPreset()
    preset = next((p for p in all_presets if p.id == args.preset_id), None)

    if not preset:
        LOG.error("Filter preset with ID %d does not exist!",
                  args.preset_id)
        sys.exit(1)
    try:
        success = client.deleteFilterPreset(args.preset_id)

        if success:
            LOG.info(
                "Filter preset '%s' (ID: %d) "
                "successfully deleted.",
                preset.name, args.preset_id)
        else:
            LOG.error("An error occurred when deleting the filter preset.")
            sys.exit(1)
    except Exception as e:
        LOG.error("An error occurred while deleting the filter preset: %s", e)
        sys.exit(1)
