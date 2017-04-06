# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parse the plist output of an analyzer and convert it to a report for
further processing.
"""

import plistlib
import traceback
from xml.parsers.expat import ExpatError

from libcodechecker.analyze import plist_helper
from libcodechecker.logger import LoggerFactory

from libcodechecker.report import BugPath
from libcodechecker.report import DiagSection
from libcodechecker.report import Position
from libcodechecker.report import Range
from libcodechecker.report import Report

LOG = LoggerFactory.get_new_logger('PLIST_PARSER')


def make_position(pos_map, files):
    return Position(pos_map.line, pos_map.col, files[pos_map.file])


def __handle_control(item, files):
    """
    Builds a list of DiagSections for a control section.
    """
    ctrl_diag_sections = []
    for edge in item['edges']:
        control = DiagSection('control')

        start_edge = edge['start']
        end_edge = edge['end']

        # Edge element has start range.
        start_pos_s = make_position(start_edge[0], files)
        start_pos_e = make_position(start_edge[1], files)
        start_range = Range(start_pos_s, start_pos_e)

        # Edge element has end range.
        end_pos_s = make_position(end_edge[0], files)
        end_pos_e = make_position(end_edge[1], files)
        end_range = Range(end_pos_s, end_pos_e)

        control.start_range = start_range
        control.end_range = end_range
        ctrl_diag_sections.append(control)

    return ctrl_diag_sections


def __handle_event(item, files):
    """
    Builds a DiagSection for an event section.
    """
    message = item['message']

    event = DiagSection('event', message)

    # Every event should have a location.
    item_loc = item['location']
    if item_loc:
        location = make_position(item['location'],
                                 files)
        event.location = location

    # Events might have ranges but it is optional.
    ranges = item.get('ranges')
    if ranges:
        start = make_position(ranges[0][0], files)
        start_range = Range(start)

        end = make_position(ranges[0][1], files)
        end_range = Range(end)

        event.start_range = start_range
        event.end_range = end_range

    # An event migth have an extended message.
    event.extended_msg = item.get('extended_message', '')

    return event


def parse_plist(path):
    """
    Parse the reports from a plist file.
    One plist file can contain multiple reports.
    """
    LOG.debug("Parsing plist: " + path)

    reports = []
    files = []
    try:
        plist = plistlib.readPlist(path)

        files = plist['files']

        for diag in plist['diagnostics']:

            message = diag['description']
            checker_name = diag.get('check_name')
            if not checker_name:
                LOG.debug("Check name wasn't found in the plist file. "
                          "Read the user guide!")
                checker_name = plist_helper.get_check_name(message)
                LOG.debug('Guessed check name: ' + checker_name)

            hash_value = diag.get('issue_hash_content_of_line_in_context')

            new_report = Report(checker_name,
                                hash_value,
                                diag['category'],
                                diag['type'])

            # Set the main diagnostic section used at the listing of reports.
            start_pos = Position(line=diag['location']['line'],
                                 col=diag['location']['col'],
                                 filepath=files[diag['location']['file']])

            main_section = DiagSection(kind="main", msg=message)
            main_range = Range(start_pos)
            main_section.start_range = main_range
            main_section.end_range = main_range

            new_report.main_section = main_section

            # Build a bug path from the DiagSections.
            # NOTE: the order of the elements matter!
            bug_path_items = []
            for item in diag['path']:
                # Only event and control items are added to the path.
                if item['kind'] == 'event':
                    event = __handle_event(item, files)
                    bug_path_items.append(event)

                elif item['kind'] == 'control':
                    ctrl_sections = __handle_control(item, files)
                    for cs in ctrl_sections:
                        bug_path_items.append(cs)
                else:
                    LOG.warning('Not supported item kind "' + item['kind'] +
                                '" found during plist parsing.')

            new_report.set_path(BugPath(bug_path_items))

            reports.append(new_report)

    except ExpatError as err:
        LOG.error('Failed to process plist file: ' + path +
                  ' wrong file format?')
        LOG.error(err)
    except AttributeError as ex:
        LOG.error('Failed to get important report data from plist.')
        LOG.error(ex)
    except Exception as ex:
        LOG.error('Error during processing reports from the plist file: ' +
                  path)
        LOG.error(ex)
    finally:
        return files, reports
