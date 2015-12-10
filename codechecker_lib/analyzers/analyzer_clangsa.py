# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import shlex
import subprocess
import StringIO

from codechecker_lib import logger

from codechecker_lib.analyzers import analyzer_base

LOG = logger.get_new_logger('CLANGSA')

class ClangSA(analyzer_base.SourceAnalyzer):
    """
    constructs clang static analyzer commmands
    """

    def get_analyzer_checkers(self, env):
        """
        return the list of the supported checkers
        """
        config = self.config_handler
        analyzer_binary = config.analyzer_binary

        command = [analyzer_binary, "-cc1"]
        for plugin in config.analyzer_plugins:
            command.append("-load")
            command.append(plugin)
        command.append("-analyzer-checker-help")

        try:
            command = shlex.split(' '.join(command))
            result = subprocess.check_output(command,
                                             env=env)
        except subprocess.CalledProcessError as cperr:
            LOG.error(cperr)
            return ''

        output = StringIO.StringIO()
        output.write('Checkers available in Clang Static Analyzer\n')
        output.write('-------------------------------------------\n')
        output.write(result)
        res = output.getvalue()
        output.close()
        return res

    def construct_analyzer_cmd(self, res_handler):
        """
        called by the analyzer method
        construct the analyzer command
        """
        try:
            # get an putput file from the result handler
            analyzer_output_file = res_handler.get_analyzer_result_file()

            analyzer_mode = 'plist-multi-file'

            # get the checkers list from the config_handler
            # checker order matters
            config = self.config_handler

            analyzer_bin = config.analyzer_binary
            analyzer_plugins = config.analyzer_plugins

            # raw config data in text
            config_data = config.config_data

            analyzer_cmd = []

            analyzer_cmd.append(analyzer_bin)

            if len(config.compiler_resource_dirs) > 0:
                for inc_dir in config.compiler_resource_dirs:
                    analyzer_cmd.append('-resource-dir')
                    analyzer_cmd.append(inc_dir)
                    analyzer_cmd.append('-isystem')
                    analyzer_cmd.append(inc_dir)

            # compiling is enough
            analyzer_cmd.append('-c')

            analyzer_cmd.append('--analyze')

            # turn off clang hardcoded checkers list
            analyzer_cmd.append('--analyzer-no-default-checks')

            for plugin in config.analyzer_plugins:
                analyzer_cmd.append("-Xclang")
                analyzer_cmd.append("-load")
                analyzer_cmd.append("-Xclang")
                analyzer_cmd.append(plugin)

            if config.analyzer_plugins:
                analyzer_cmd.append('-Xclang')
                analyzer_cmd.append('-plugin')
                analyzer_cmd.append('-Xclang')
                analyzer_cmd.append('checkercfg')

            analyzer_cmd.append('-Xclang')
            analyzer_cmd.append('-analyzer-opt-analyze-headers')
            analyzer_cmd.append('-Xclang')
            analyzer_cmd.append('-analyzer-output=' + analyzer_mode)

            if config.compiler_sysroot:
                analyzer_cmd.append('--sysroot')
                analyzer_cmd.append(self._context.compiler_sysroot)

            for path in config.system_includes:
                analyzer_cmd.append('-isystem')
                analyzer_cmd.append(path)

            for path in config.includes:
                analyzer_cmd.append('-I')
                analyzer_cmd.append(path)

            analyzer_cmd.append('-o')
            analyzer_cmd.append(analyzer_output_file)

            for checker_name, enabled in config.checks():
                if enabled:
                    analyzer_cmd.append('-Xclang')
                    analyzer_cmd.append('-analyzer-checker=' + checker_name)
                else:
                    analyzer_cmd.append('-Xclang')
                    analyzer_cmd.append('-analyzer-disable-checker')
                    analyzer_cmd.append('-Xclang')
                    analyzer_cmd.append(checker_name)

            # Set lang
            analyzer_cmd.append('-x')
            analyzer_cmd.append(self.buildaction.lang)

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            analyzer_cmd.append(self.source_file)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []
