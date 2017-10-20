# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Calculates call statistics from analysis output
"""
import os
import subprocess
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('STATISTIC_COLLECTOR')


def create_statistics(clang_output_dir, stats_dir):

    # Statistics yaml files will be stored in stats_dir
    script_path = os.path.dirname(os.path.realpath(__file__))
    try:
        os.stat(stats_dir)
    except:
        os.mkdir(stats_dir)

    clang_outs = []
    try:
        for f in os.listdir(clang_output_dir):
            if os.path.isfile(os.path.join(clang_output_dir, f)):
                clang_outs.append(os.path.join(clang_output_dir, f))
    except OSError as oerr:
        LOG.debug(ex)
        LOG.warning("Statistics can not be collected.")
        LOG.warning("Analyzer output error.")
        return

    if len(clang_outs) == 0:
        return

    unchecked_yaml = os.path.join(stats_dir, "UncheckedReturn.yaml")

    ret_val_cmd = os.path.join(script_path, "statistics",
                               "gen_yaml_for_return_value_checks.py")
    cmd_arg = [ret_val_cmd]
    cmd_arg.extend(clang_outs)
    with open(unchecked_yaml, 'w') as unchecked_file:
        subprocess.Popen(cmd_arg, stdout=unchecked_file)
    LOG.debug("Statistics successfully generated into: " + unchecked_yaml)

    special_ret_yaml = os.path.join(stats_dir, "SpecialReturn.yaml")

    special_ret_val = os.path.join(script_path, "statistics",
                                   "gen_yaml_for_special_return_values.py")
    cmd_arg = [special_ret_val]
    cmd_arg.extend(clang_outs)
    with open(special_ret_yaml, 'w') as unchecked_file:
        subprocess.Popen(cmd_arg, stdout=unchecked_file)
    LOG.debug("Statistics successfully generated into: " + special_ret_yaml)
