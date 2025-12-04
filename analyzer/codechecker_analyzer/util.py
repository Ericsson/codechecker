# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Utility functions for the CodeChecker analyzer.
"""

import os
import shlex
import hashlib


def analyzer_action_hash(analyzed_source_file, build_dir, build_command):
    source_file = os.path.normpath(
        os.path.join(build_dir,
                     analyzed_source_file))

    # In case of "make 4.3" depending on compile-time options "make" tool
    # can be built so a subprocess named cc1build will be logged by
    # "CodeChecker log".
    # See posix_spawn() option:
    # https://lists.gnu.org/archive/html/info-gnu/2020-01/msg00004.html
    # In this case the -o output argument of cc1build command is a randomly
    # named temporary file. We can't afford dynamic parts in the original
    # build command, because its hash is used for identification in the
    # plist file name.
    #
    # The proper logging of this "make 4.3" version has been done in
    # bf140d6, so it is unlikely happen that two build actions differ only
    # in their "-o" flags. This workaround is still kept for any case.
    #
    # Note that some information loss occurs during the following algorithm
    # because ' '.join(shlex.split(cmd)) is not necessarily equal to cmd:
    # g++ -DVAR="hello world" main.cpp

    args = shlex.split(build_command)
    indices = [idx for idx, v in enumerate(args) if v.startswith('-o')]

    for idx in reversed(indices):
        # Output can be given separate or joint:
        # -o a.out vs. -oa.out
        # In the first case we delete its argument too.
        if args[idx] == '-o':
            del args[idx]
        del args[idx]

    build_info = source_file + '_' + ' '.join(args)

    return hashlib.md5(build_info.encode(errors='ignore')).hexdigest()
