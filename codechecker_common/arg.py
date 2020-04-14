# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""Argument parsing related helper classes and functions."""


import argparse
import textwrap


class RawDescriptionDefaultHelpFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter
):
    """
    Adds default values to argument help and retains any formatting in
    descriptions.
    """
    def _split_lines(self, text, width):
        """ Split the lines.

        If the text parameter starts with 'R|' it will keep whitespaces and
        it will wrapp the content. Otherwise it will call the parent function
        of RawDescriptionHelpFormatter.
        """
        if text.startswith('R|'):
            lines = [textwrap.wrap(line, width, replace_whitespace=False)
                     for line in text[2:].lstrip().splitlines()]
            return [line for sublines in lines for line in sublines]

        return argparse.RawDescriptionHelpFormatter._split_lines(self, text,
                                                                 width)
