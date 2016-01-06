# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import re
import json
import shlex
import argparse
import StringIO

from codechecker_lib.analyzers import config_handler

from codechecker_lib import logger

LOG = logger.get_new_logger('CLANG TIDY CONFIG')

class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    '''
    Configuration handler for Clang-tidy analyzer
    '''

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()
        # disable by default enabled checks in clang tidy
        self.__checks = '-*'

    def set_checks(self, checks):
        """
        simple string
        """
        self.__checks = checks

    def add_checks(self, checks):
        """
        """
        if checks != '':
            self.__checks = self.__checks + ',' + checks

    def checks(self):
        """
        """
        return self.__checks

    def checks_str(self):
        """
        return the checkers formatted for printing
        """
        output = StringIO.StringIO()
        output.write('Default checkers set for Clang Tidy:\n')
        output.write('------------------------------------\n')
        output.write(self.__checks)
        res = output.getvalue()
        output.close()
        return res

    def get_checker_configs(self):
        """
        process the raw extra analyzer arguments and get the configuration
        data ('-config=' argument for Clang tidy) for the checkers

        Clang tidy accepts YAML or JSON formatted config, right now
        parsing only the JSON format is supported

        return a lis of tuples
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
        LOG.debug(self.analyzer_extra_arguments)

        res = []

        # match for clang static analyzer names and attributes
        clang_sa_checker_rex = r'^clang-analyzer-(?P<checker_name>([^:]+))\:(?P<checker_attribute>([^:]+))$'

        # match for clang tidy analyzer names and attributes
        clang_tidy_checker_rex = r'^(?P<checker_name>([^.]+))\.(?P<checker_attribute>([^.]+))$'

        clangsa_pattern = re.compile(clang_sa_checker_rex)
        tidy_pattern = re.compile(clang_tidy_checker_rex)

        # get config from the extra arguments if there is any
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
            tidy_config = json.loads(args.tidy_config)
            for checker_option in tidy_config.get('CheckOptions', []):
                value = checker_option['value']
                key_values = re.match(clangsa_pattern, checker_option['key'])
                key_values_tidy = re.match(tidy_pattern, checker_option['key'])
                if key_values:
                    checker_name = key_values.group('checker_name')
                    checker_attr = key_values.group('checker_attribute')
                    res.append((checker_name, checker_attr, value))
                elif key_values_tidy:
                    checker_name = key_values_tidy.group('checker_name')
                    checker_attr = key_values_tidy.group('checker_attribute')
                    res.append((checker_name, checker_attr, value))
                else:
                    LOG.debug('no match')
        except ValueError as verr:
            LOG.debug('Failed to parse config')
            LOG.debug(verr)
        except Exception as ex:
            LOG.debug('Failed to process config')
            LOG.debug(ex)

        return res
