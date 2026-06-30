# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import random
import string
import unittest

from codechecker_analyzer.analyzers.result_handler_base import ResultHandler


class BuildAction:
    directory = os.path.abspath(os.sep)
    analyzer_type = 'clangsa'
    original_command = None


class ResultHandlerTest(unittest.TestCase):
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
        rh = ResultHandler(ba, os.path.join(os.path.abspath(os.sep),
                                            'workspace'))
        rh.analyzed_source_file = 'main.cpp'

        ba.original_command = \
            f'g++ main.cpp -o {random_string()} -o{random_string()}'
        hash1 = rh.analyzer_action_str

        ba.original_command = \
            f'g++ main.cpp -o {random_string()} -o{random_string()}'
        hash2 = rh.analyzer_action_str

        # Hash must be stable regardless of -o arguments.
        self.assertEqual(hash1, hash2)

        ba.original_command = \
            f'g++ main.cpp -o {random_string()} -o{random_string()} -W -O3'
        hash3 = rh.analyzer_action_str

        ba.original_command = \
            f'g++ main.cpp -o {random_string()} -o{random_string()} -W -O3'
        hash4 = rh.analyzer_action_str

        # Hash must be stable regardless of -o arguments.
        self.assertEqual(hash3, hash4)
        # Different flags produce different hashes.
        self.assertNotEqual(hash1, hash3)
