# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Contains functions to format and pretty-print data from two-dimensional arrays.
"""


import json

from operator import itemgetter
from typing import Iterable, List, Optional

from prettytable import PrettyTable, SINGLE_BORDER


def to_str(
    format_name: str,
    keys,
    rows,
    sort_by_column_number: Optional[int] = None,
    rev=False,
    separate_footer=False
) -> str:
    """
    Converts the given two-dimensional array (with the specified keys)
    to the given format.
    """
    if sort_by_column_number is not None:
        rows.sort(key=itemgetter(sort_by_column_number), reverse=rev)

    all_rows = rows
    if keys:
        all_rows = [keys] + list(rows)

    if format_name == 'rows':
        return to_rows(rows)
    elif format_name in ('table', 'plaintext'):
        # TODO: 'plaintext' for now to support the 'CodeChecker cmd' interface.
        return to_table(all_rows, True, separate_footer)
    elif format_name == 'csv':
        return to_csv(all_rows)
    elif format_name == 'dictlist':
        return to_dictlist(keys, rows)
    elif format_name == 'json':
        return json.dumps(to_dictlist(keys, rows))
    else:
        raise ValueError("Unsupported format")


def to_rows(lines: Iterable[str]) -> str:
    """
    Prints the given rows with minimal formatting.
    """

    str_parts = []

    lns: List[List[str]] = [
        ['' if e is None else e for e in line] for line in lines]

    # Count the column width.
    widths: List[int] = []
    for line in lns:
        for i, size in enumerate([len(str(x)) for x in line]):
            while i >= len(widths):
                widths.append(0)
            if size > widths[i]:
                widths[i] = size

    # Generate the format string to pad the columns.
    print_string = " "
    for i, width in enumerate(widths):
        if i == 0 or i == len(widths) - 1 or width == 0:
            print_string += "{" + str(i) + "} "
        else:
            print_string += "{" + str(i) + ":" + str(width) + "} "

    if not print_string:
        return ''

    print_string = print_string[:-1]

    # Print the actual data.
    for i, line in enumerate(lns):
        try:
            str_parts.append(print_string.format(*line))
        except IndexError:
            # pylint: disable=raise-missing-from
            raise TypeError("One of the rows have a different number of "
                            "columns than the others")

    return '\n'.join(str_parts)


def to_table(
    lines: Iterable[str],
    separate_head=True,
    separate_footer=False
) -> str:
    """
    Pretty-prints the given two-dimensional array's lines using PrettyTable.
    Produces clean, properly-aligned tables that handle long lines gracefully.
    The first row is used as the header when separate_head is True.
    """
    lns: List[List[str]] = [
        ['' if e is None else str(e) for e in line] for line in lines]

    if not lns:
        return ''

    table = PrettyTable()
    table.set_style(SINGLE_BORDER)

    if separate_head:
        table.field_names = lns[0]
        data_rows = lns[1:]
    else:
        # No header: use unique placeholder names and hide the header row
        table.field_names = [str(i) for i in range(len(lns[0]))]
        table.header = False
        data_rows = lns

    for row in data_rows:
        table.add_row(row)

    # Align all columns to the left for consistency with the old format
    for field in table.field_names:
        table.align[field] = 'l'

    return table.get_string()


def to_csv(lines: Iterable[str]) -> str:
    """
    Pretty-print the given two-dimensional array's lines in CSV format.
    """

    str_parts = []

    lns: List[List[str]] = [
        ['' if e is None else e for e in line] for line in lines]

    # Count the columns.
    columns = 0 if len(lns) == 0 else max(map(len, lns))

    print_string = ""
    for i in range(columns):
        print_string += "{" + str(i) + "},"

    if not print_string:
        return ''

    print_string = print_string[:-1]

    # Print the actual data.
    for line in lns:
        try:
            str_parts.append(print_string.format(*line))
        except IndexError:
            # pylint: disable=raise-missing-from
            raise TypeError("One of the rows have a different number of "
                            "columns than the others")

    return '\n'.join(str_parts)


def to_dictlist(key_list, lines):
    """
    Pretty-print the given two-dimensional array's lines into a JSON
    object list. The key_list acts as the "header" of the table, specifying the
    keys to use in the resulting object.

    This function expects values to be the same number as the length of
    key_list, and that the order of values in a line corresponds to the order
    of keys.
    """

    res = []
    for line in lines:
        res.append(dict(zip(key_list, line)))

    return res
