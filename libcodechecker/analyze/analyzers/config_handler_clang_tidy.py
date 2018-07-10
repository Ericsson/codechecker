# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Config handler for Clang Tidy analyzer.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import json
import re
import shlex

from libcodechecker.analyze.analyzers import config_handler
from libcodechecker.logger import get_logger

LOG = get_logger('analyzer.tidy')


class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer.
    """

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()

    def get_checker_configs(self):
        """
        Process the raw extra analyzer arguments and get the configuration
        data ('-config=' argument for Clang tidy) for the checkers.

        Clang tidy accepts YAML or JSON formatted config, right now
        parsing only the JSON format is supported.

        Return a list of tuples
        (checker_name, key, key_value) list

        {
         "CheckOptions": [
           {
           "key": "readability-simplify-boolean-expr.ChainedConditionalReturn",
           "value": 1
           },
           {
           "key": "google-readability-namespace-comments.SpacesBeforeComments",
           "value": 2
           },
           {
           "key": "modernize-loop-convert.NamingStyle",
           "value": "UPPER_CASE"
           },
           {
           "key": "clang-analyzer-unix.Malloc:Optimistic",
           "value": true
           },
           {
           "key": "clang-analyzer-unix.test.Checker:Optimistic",
           "value": true
           }
         ]
        }
        """
        LOG.debug("Tidy extra args: " + self.analyzer_extra_arguments)

        res = []

        # Get config from the extra arguments if there is any.
        try:
            tidy_config_parser = argparse.ArgumentParser()
            tidy_config_parser.add_argument('-config',
                                            dest='tidy_config',
                                            default='',
                                            type=str)

            args, _ = tidy_config_parser.parse_known_args(
                shlex.split(self.analyzer_extra_arguments))

        except Exception as ex:
            LOG.debug('No config found in the tidy extra args.')
            LOG.debug(ex)
            return res

        try:
            # Match for clang tidy analyzer names and attributes.
            clang_tidy_checker_rex = r'^(?P<checker_name>([^.]+))' \
                                     r'\.(?P<checker_attribute>([^.]+))$'

            tidy_pattern = re.compile(clang_tidy_checker_rex)
            tidy_config = json.loads(args.tidy_config)
            for checker_option in tidy_config.get('CheckOptions', []):
                value = checker_option['value']
                # We only store configs related to tidy checks. We run static
                # analyzer separately, so it does not affect the SA invocation.
                key_values_tidy = re.match(tidy_pattern, checker_option['key'])
                if key_values_tidy:
                    checker_name = key_values_tidy.group('checker_name')
                    checker_attr = key_values_tidy.group('checker_attribute')
                    res.append((checker_name, checker_attr, value))
                else:
                    LOG.debug('no match')
        except ValueError as verr:
            LOG.debug('Failed to parse config.')
            LOG.debug(verr)
        except Exception as ex:
            LOG.debug('Failed to process config.')
            LOG.debug(ex)

        return res

    def enable_checker(self, checker_name, description=None):
        """
        Enable checker, keep description if already set.
        """
        if checker_name.startswith("W"):
            self.add_checker(checker_name, True, None)
            return

        super(ClangTidyConfigHandler, self).enable_checker(checker_name,
                                                           description)

    def disable_checker(self, checker_name, description=None):
        """
        Disable checker, keep description if already set.
        """
        if checker_name.startswith("Wno-") or checker_name.startswith("W"):
            self.add_checker(checker_name, False, None)
            return

        super(ClangTidyConfigHandler, self).disable_checker(checker_name,
                                                            description)
