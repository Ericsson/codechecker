# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
'CodeChecker store' parses a list of analysis results and stores them in the
database.
"""

import argparse
import functools
import json
import multiprocessing
import os
import sys
import tempfile
import traceback

from libcodechecker import generic_package_context
from libcodechecker import host_check
from libcodechecker import util
from libcodechecker.analyze import skiplist_handler
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.libclient.client import setup_client
from libcodechecker.log import build_action
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory


LOG = LoggerFactory.get_new_logger('STORE')


def full_traceback(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            msg = "{}\n\nOriginal {}".format(e, traceback.format_exc())
            raise type(e)(msg)
    return wrapper


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker store',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Store the results from one or more 'codechecker-"
                       "analyze' result files in a database.",

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': "The results can be viewed by connecting to such a server "
                  "in a Web browser or via 'CodeChecker cmd'.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Save analysis results to a database."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('input',
                        type=str,
                        nargs='*',
                        metavar='file/folder',
                        default=os.path.join(util.get_default_workspace(),
                                             'reports'),
                        help="The analysis result files and/or folders "
                             "containing analysis results which should be "
                             "parsed and printed.")

    parser.add_argument('-t', '--type', '--input-format',
                        dest="input_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results were "
                             "created as.")

    parser.add_argument('-j', '--jobs',
                        type=int,
                        dest="jobs",
                        required=False,
                        default=1,
                        help="Number of threads to use in storing results. "
                             "More threads mean faster operation at the cost "
                             "of using more memory.")

    parser.add_argument('-n', '--name',
                        type=str,
                        dest="name",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="The name of the analysis run to use in storing "
                             "the reports to the database. If not specified, "
                             "the '--name' parameter given to 'codechecker-"
                             "analyze' will be used, if exists.")

    # Upcoming feature planned for v6.0. Argument name and help RESERVED.
    # parser.add_argument('--group', '--group-name',
    #                    type=str,
    #                    dest="group_name",
    #                    required=False,
    #                    default=argparse.SUPPRESS,
    #                    help="Specify the \"analysis group\" the results "
    #                         "stored will belong to. An analysis group "
    #                         "consists of multiple analyses whose reports "
    #                         "are showed together in a common view -- e.g. "
    #                         "a project's view for every subproject analysed "
    #                         "separately, or all analyses of a user or a "
    #                         "team.")

    parser.add_argument('-f', '--force',
                        dest="force",
                        default=False,
                        action='store_true',
                        required=False,
                        help="Delete analysis results stored in the database "
                             "for the current analysis run's name and store "
                             "only the results reported in the 'input' files. "
                             "(By default, CodeChecker would keep reports "
                             "that were coming from files not affected by the "
                             "analysis, and only incrementally update defect "
                             "reports for source files that were analysed.)")

    server_args = parser.add_argument_group(
        "server arguments",
        "Specifies a 'CodeChecker server' instance which will be used to "
        "store the results. This server must be running and listening prior "
        "to the 'store' command being ran.")

    server_args.add_argument('--host',
                             type=str,
                             dest="host",
                             required=False,
                             default="localhost",
                             help="The IP address or hostname of the "
                                  "CodeChecker server.")

    server_args.add_argument('-p', '--port',
                             type=int,
                             dest="port",
                             required=False,
                             default=8001,
                             help="The port of the server to use for storing.")

    add_verbose_arguments(parser)
    parser.set_defaults(func=main)


@full_traceback
def consume_plist(item):
    try:
        f, context, metadata_dict, compile_cmds, server_data = item

        if 'working_directory' in metadata_dict:
            os.chdir(metadata_dict['working_directory'])

        buildaction = build_action.BuildAction()

        LOG.debug("Parsing input file '" + f + "'")
        analyzed_source = 'UNKNOWN'
        if 'result_source_files' in metadata_dict and\
                f in metadata_dict['result_source_files']:
                analyzed_source = metadata_dict['result_source_files'][f]

        if analyzed_source == "UNKNOWN":
            LOG.info("Storing defects in input file '" + f + "'")
        else:
            LOG.info("Storing analysis results for file '" +
                     analyzed_source + "'")

        LOG.debug("Getting build command for '" + f + "'")
        buildaction.original_command = compile_cmds.get(analyzed_source,
                                                        'MISSING')

        if buildaction.original_command == 'MISSING':
            # Create a "good enough" command based on the plist's name, so
            # even without a build command, we can still store the results.
            LOG.warning("Compilation action was not found for file '" +
                        analyzed_source + "' (input '" + f + "')")
            LOG.debug("Considering results in input '" + f + "' brand new.")
            buildaction.original_command = f

        rh = analyzer_types.construct_store_handler(buildaction,
                                                    context.run_id,
                                                    context.severity_map)

        rh.analyzer_returncode = 0
        rh.analyzer_result_file = f
        rh.analyzer_cmd = ''
        rh.analyzed_source_file = analyzed_source

        host, port = server_data
        client = setup_client(host, port, '/')
        rh.handle_results(client)
        return 0
    except Exception as ex:
        LOG.warning(str(ex))
        LOG.warning("Failed to process report: " + f)
        return 1


def __get_run_name(input_list):
    """Create a runname for the stored analysis from the input list."""

    # Try to create a name from the metada JSON(s).
    names = []
    for input_path in input_list:
        metafile = os.path.join(input_path, "metadata.json")
        if os.path.isdir(input_path) and os.path.exists(metafile):
            with open(metafile, 'r') as metadata:
                metajson = json.load(metadata)

            if 'name' in metajson:
                names.append(metajson['name'])
            else:
                names.append("unnamed result folder")

    if len(names) == 1 and names[0] != "unnamed result folder":
        return names[0]
    elif len(names) > 1:
        return "multiple projects: " + ', '.join(names)
    else:
        return False


def res_handler(results):
    """
    Summary about the parsing and storage results.
    """
    LOG.info("Finished processing and storing reports.")
    LOG.info("Failed: " + str(results.count(1)) + "/" + str(len(results)))
    LOG.info("Successful " + str(results.count(0)) + "/" + str(len(results)))


def process_compile_db(compile_db):
    """
    Create a dict where the source file name (absolute path) is the key and
    the correspoding compilation command is the value.
    """
    compile_db = os.path.abspath(compile_db)
    comp_cmds = {}

    if not os.path.exists(compile_db):
        LOG.warning("Compilation command file '" + compile_db +
                    "' is missing.")
        LOG.warning("Update mode will not work, without compilation "
                    "command it is not known which file to update.")
        return comp_cmds

    with open(compile_db, 'r') as ccdb:
        comp_cmds = json.load(ccdb)

    processed = {}
    for cc in comp_cmds:
        file_path = os.path.join(cc['directory'], cc['file'])
        try:
            # Newer compile command json format.
            processed[file_path] = str(' '.join(cc['arguments']))
        except Exception:
            processed[file_path] = cc['command']

    return processed


def main(args):
    """
    Store the defect results in the specified input list as bug reports in the
    database.
    """

    if not host_check.check_zlib():
        raise Exception("zlib is not available on the system!")

    # To ensure the help message prints the default folder properly,
    # the 'default' for 'args.input' is a string, not a list.
    # But we need lists for the foreach here to work.
    if isinstance(args.input, str):
        args.input = [args.input]

    if 'name' not in args:
        LOG.debug("Generating name for analysis...")
        generated = __get_run_name(args.input)
        if generated:
            setattr(args, 'name', generated)
        else:
            LOG.error("No suitable name was found in the inputs for the "
                      "analysis run. Please specify one by passing argument "
                      "--name run_name in the invocation.")
            sys.exit(2)  # argparse returns error code 2 for bad invocations.

    LOG.info("Storing analysis results for run '" + args.name + "'")

    if args.force:
        LOG.info("argument --force was specified: the run with name '" +
                 args.name + "' will be deleted.")

    context = generic_package_context.get_context()

    original_cwd = os.getcwd()
    empty_metadata = {'working_directory': original_cwd}

    check_commands = []
    check_durations = []
    skip_handlers = []
    items = []

    server_data = (args.host, args.port)

    for input_path in args.input:
        input_path = os.path.abspath(input_path)

        # WARN: analyze command should create this file!
        cmp_db = os.path.join(input_path, 'compile_cmd.json')
        compile_commands = process_compile_db(cmp_db)

        LOG.debug("Parsing input argument: '" + input_path + "'")

        if os.path.isfile(input_path):
            if not input_path.endswith(".plist"):
                continue

            items.append((input_path,
                          context,
                          empty_metadata,
                          compile_commands,
                          server_data))

        elif os.path.isdir(input_path):
            metadata_file = os.path.join(input_path, "metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as metadata:
                    metadata_dict = json.load(metadata)
                    LOG.debug(metadata_dict)

                    if 'command' in metadata_dict:
                        check_commands.append(metadata_dict['command'])
                    if 'timestamps' in metadata_dict:
                        check_durations.append(
                            float(metadata_dict['timestamps']['end'] -
                                  metadata_dict['timestamps']['begin']))
                    if 'skip_data' in metadata_dict:
                        # Save previously stored skip data for sending to the
                        # database, to ensure skipped headers are actually
                        # skipped --- 'analyze' can't do this.
                        handle, path = tempfile.mkstemp()
                        with os.fdopen(handle, 'w') as tmpf:
                            tmpf.write('\n'.join(metadata_dict['skip_data']))

                        skip_handlers.append(
                            skiplist_handler.SkipListHandler(path))
                        os.remove(path)
            else:
                metadata_dict = empty_metadata

            _, _, files = next(os.walk(input_path), ([], [], []))
            for f in files:
                if not f.endswith(".plist"):
                    continue

                items.append((os.path.join(input_path, f),
                              context, metadata_dict, compile_commands,
                              server_data))

    if len(check_commands) == 0:
        command = ' '.join(sys.argv)
    elif len(check_commands) == 1:
        command = ' '.join(check_commands[0])
    else:
        command = "multiple analyze calls: " +\
                  '; '.join([' '.join(com) for com in check_commands])

    # setup connection to the remote server
    client = setup_client(args.host,
                          args.port, '/')

    LOG.debug("Initializing client connecting to " +
              str(args.host) + ":" + str(args.port) + " done.")
    context.run_id = client.addCheckerRun(command,
                                          args.name,
                                          context.version,
                                          args.force)

    # Send previously collected skip information to the server.
    LOG.debug("Storing skip information")
    for skip_handler in skip_handlers:
        if not client.addSkipPath(context.run_id, skip_handler.get_skiplist()):
            LOG.debug("Adding skip path failed!")

    # TODO: This is a hotfix for a data race problem in storage.
    # Currently removal of build actions is based on plist files which lack
    # build command that is needed for unambiguous deletion.
    args.jobs = 1

    pool = multiprocessing.Pool(args.jobs)

    try:
        pool.map_async(consume_plist,
                       items,
                       1,
                       callback=lambda results: res_handler(results)
                       ).get(float('inf'))

        pool.close()
    except Exception:
        pool.terminate()
        raise  # CodeChecker.py is the invoker, it will handle this.
    finally:
        pool.join()
        os.chdir(original_cwd)

    client.finishCheckerRun(context.run_id)

    if len(check_durations) > 0:
        client.setRunDuration(context.run_id,
                              # Round the duration to seconds.
                              int(sum(check_durations)))
    return
