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
import shutil

from operator import itemgetter
from typing import Iterable, List, Optional

from prettytable import HRuleStyle, PrettyTable, TableStyle


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


def _compute_natural_widths(
    field_names: List[str],
    data_rows: List[List[str]],
    show_header: bool,
) -> List[int]:
    """
    Return the natural content width of each column (no truncation applied).

    The natural width is the maximum of the header length (when shown) and
    the length of every data cell in that column.
    """
    widths: List[int] = (
        [len(str(h)) for h in field_names] if show_header
        else [0] * len(field_names)
    )
    for row in data_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    return widths


def _fit_table_to_width(
    table: PrettyTable,
    nat_widths: List[int],
    terminal_width: int,
) -> str:
    """
    Render ``table`` so that it fits within ``terminal_width`` columns.

    The algorithm avoids hard-coding column types by working from the
    pre-computed natural widths of each column.  Short columns (those that
    already fit their share of the available space) keep their full natural
    width; only the longer columns are shortened, proportionally.

    The iteration is a fixpoint loop:

    1. Each unassigned column gets a *proportional share* of the remaining
       content budget (based on its natural width relative to the total of
       all unassigned columns).
    2. Any column whose natural width fits within its share is *locked in*
       at that natural width, freeing up space for the others.
    3. Repeat until no more columns can be locked.
    4. Distribute the residual budget among whatever columns are still
       unassigned.
    5. Apply ``max_table_width`` as a final safety net to absorb rounding
       errors.

    The per-column border/padding overhead for SINGLE_BORDER style is
    3 characters per column (space + content + space + border) plus 1 for
    the leading border: ``overhead = num_cols * 3 + 1``.
    """
    num_cols = len(nat_widths)
    # SINGLE_BORDER layout: │ c1 │ c2 │ … │ cn │
    # overhead = 1 (left border) + num_cols *
    #            (1 space + content + 1 space + 1 border)
    #          = 1 + num_cols * 3
    overhead = num_cols * 3 + 1

    total_natural = sum(nat_widths) + overhead

    # If the table already fits, render it without any truncation.
    if total_natural <= terminal_width:
        return table.get_string()

    # Minimum content width per column (must show at least a few characters).
    min_col_width = 4

    # Available content budget (sum of column widths must be <= this).
    available = max(terminal_width - overhead, num_cols * min_col_width)

    # --- Iterative fixpoint ---
    # assigned[i] holds the final max_width for column i once locked.
    # Initialised to 0; every entry is guaranteed to be set before use.
    assigned: List[int] = [0] * num_cols
    unassigned = list(range(num_cols))
    remaining = available

    # Each iteration locks columns whose natural width fits their proportional
    # share, freeing up the remaining budget for the wider columns.
    for _ in range(num_cols + 1):
        if not unassigned:
            break

        nat_sum = sum(nat_widths[i] for i in unassigned)
        locked_this_round = []

        for i in unassigned:
            if nat_sum > 0:
                share = max(min_col_width,
                            int(nat_widths[i] / nat_sum * remaining))
            else:
                share = max(min_col_width, remaining // len(unassigned))

            if nat_widths[i] <= share:
                locked_this_round.append((i, nat_widths[i]))

        if not locked_this_round:
            break  # Nothing new was locked; exit early.

        for i, w in locked_this_round:
            assigned[i] = w
            remaining -= w
            unassigned.remove(i)

    # Distribute remaining budget among columns still unassigned
    # (those that need truncation), proportionally to natural widths.
    if unassigned:
        nat_sum = sum(nat_widths[i] for i in unassigned)
        for i in unassigned:
            if nat_sum > 0:
                share = max(min_col_width,
                            int(nat_widths[i] / nat_sum * remaining))
            else:
                share = max(min_col_width, remaining // len(unassigned))
            assigned[i] = share

    # Apply per-column max_width constraints.
    for i, fn in enumerate(table.field_names):
        table.max_width[fn] = assigned[i]  # type: ignore[index]

    # Apply max_table_width as a safety net to absorb integer-division
    # rounding errors that might push the rendered width over the limit.
    table.max_table_width = terminal_width

    return table.get_string()


def _make_table(
    field_names: List[str],
    data_rows: List[List[str]],
    show_header: bool,
    hrules: HRuleStyle = HRuleStyle.FRAME
) -> PrettyTable:
    """Build and return a configured PrettyTable (without rendering it)."""
    table = PrettyTable()
    table.set_style(TableStyle.SINGLE_BORDER)
    table.field_names = field_names
    table.header = show_header
    table.hrules = hrules
    table.align = 'l'  # type: ignore[assignment]
    for row in data_rows:
        table.add_row(row)
    return table


def to_table(
    lines: Iterable[str],
    separate_head=True,
    separate_footer=False
) -> str:
    """
    Pretty-prints the given two-dimensional array's lines using PrettyTable.

    The output automatically fits within the current terminal width so that
    wide result sets no longer break across multiple screen lines.  Column
    widths are computed from the actual data: short columns (ones that already
    fit their proportional share of the available space) keep their full
    natural width; only the wider columns are shortened, proportionally.

    The first row is used as the header when ``separate_head`` is True.
    When ``separate_footer`` is True, the last data row is visually separated
    from the rest by drawing a horizontal rule between every row.
    """
    lns: List[List[str]] = [
        ['' if e is None else str(e) for e in line] for line in lines]

    if not lns:
        return ''

    # Detect the current terminal width; fall back to 80 columns when stdout
    # is redirected to a file/pipe (which is the common case in tests).
    terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns

    if separate_head:
        field_names = lns[0]
        data_rows = lns[1:]
        show_header = True
    else:
        field_names = [str(i) for i in range(len(lns[0]))]
        data_rows = lns
        show_header = False

    if separate_footer and len(data_rows) > 1:
        table = _make_table(field_names, data_rows, show_header,
                            hrules=HRuleStyle.ALL)
    else:
        table = _make_table(field_names, data_rows, show_header)

    nat_widths = _compute_natural_widths(field_names, data_rows, show_header)
    return _fit_table_to_width(table, nat_widths, terminal_width)


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
    object list. The key_list acts as the "header" of the table, specifying
    the keys to use in the resulting object.

    This function expects values to be the same number as the length of
    key_list, and that the order of values in a line corresponds to the order
    of keys.
    """

    res = []
    for line in lines:
        res.append(dict(zip(key_list, line)))

    return res
