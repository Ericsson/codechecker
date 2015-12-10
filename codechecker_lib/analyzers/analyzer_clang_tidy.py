# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
'''

import subprocess
import StringIO
import shlex

from codechecker_lib import logger

from codechecker_lib.analyzers import analyzer_base

LOG = logger.get_new_logger('CLANG TIDY')


class ClangTidy(analyzer_base.SourceAnalyzer):
    """
    constructs the clang tidy analyzer commands
    """

    def get_analyzer_checkers(self, env):
        """
        return the list of the supported checkers
        """
        config = self.config_handler
        analyzer_binary = config.analyzer_binary

        command = [analyzer_binary]
        command.append("-list-checks")
        command.append("-checks='*'")
        command.append("-")
        command.append("--")

        try:
            command = shlex.split(' '.join(command))
            result = subprocess.check_output(command,
                                             env=env)
        except subprocess.CalledProcessError as cperr:
            LOG.error(cperr)
            return ''

        output = StringIO.StringIO()
        output.write('Checkers available in Clang Tidy Analyzer\n')
        output.write('-----------------------------------------\n')
        # filter out clang static analyzer checkers
        # only clang tidy checkers are listed
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith('clang-analyzer-') or line =='':
                continue
            else:
                output.write(line + '\n')

        res = output.getvalue()
        output.close()
        return res


    def construct_analyzer_cmd(self, res_handler):
        """
        """
        return ''

