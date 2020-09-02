# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import random
import string
import unittest

from codechecker_analyzer.analyzers.result_handler_base import ResultHandler


class BuildAction:
    directory = '/tmp'
    analyzer_type = 'clangsa'
    original_command = None


class ResultHandlerTestNose(unittest.TestCase):
    """
    Test some functions of ResultHandler base class.
    """

    def test_analyzer_action_str(self):
        """
        Check -o removal in .plist filename generation.
        """
        def random_string():
            return ''.join(random.choice(string.ascii_letters)
                           for _ in range(10))

        ba = BuildAction()
        rh = ResultHandler(ba, '/tmp/workspace')
        rh.analyzed_source_file = 'main.cpp'

        ba.original_command = 'g++ main.cpp -o {} -o{}'.format(
            random_string(), random_string())
        self.assertEqual(
            rh.analyzer_action_str,
            'main.cpp_clangsa_b42298618a535959e9adc7807414763c')

        ba.original_command = 'g++ main.cpp -o {} -o{} -W -O3'.format(
            random_string(), random_string())
        self.assertEqual(
            rh.analyzer_action_str,
            'main.cpp_clangsa_193423e3c13026c10bc1457b7434a25a')
