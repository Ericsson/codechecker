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
import base64
import errno
import functools
from hashlib import sha256
import json
import os
import shutil
import sys
import tempfile
import traceback
import zipfile
import zlib

from libcodechecker import generic_package_context
from libcodechecker import host_check
from libcodechecker import util
from libcodechecker.analyze import plist_parser
from libcodechecker.libclient.client import setup_client
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


def assemble_zip(inputs, zip_file, client):
    temp_dir = tempfile.mkdtemp()
    LOG.debug("Assembling ZIP contents in '{0}':".format(temp_dir))

    report_dir = os.path.join(temp_dir, 'reports')
    os.makedirs(report_dir)

    source_dir = os.path.join(temp_dir, 'root')
    os.makedirs(source_dir)

    hash_to_file = {}
    # There can be files with same hash,
    # but different path.
    file_to_hash = {}

    def collect_file_hashes_from_plist(plist_file):
        try:
            files, _ = plist_parser.parse_plist(plist_file)

            for f in files:
                with open(f) as content:
                    hasher = sha256()
                    hasher.update(content.read())
                    content_hash = hasher.hexdigest()
                    hash_to_file[content_hash] = f
                    file_to_hash[f] = content_hash
        except Exception as ex:
            LOG.error('Parsing the plist failed: ' + str(ex))

    try:
        for input_path in inputs:
            input_path = os.path.abspath(input_path)

            if not os.path.exists(input_path):
                raise OSError(errno.ENOENT,
                              "Input path does not exist", input_path)

            if os.path.isfile(input_path):
                if not input_path.endswith(".plist"):
                    continue
                LOG.debug("Copying plist '{0}' to ZIP assembly dir..."
                          .format(input_path))
                shutil.copy(input_path, report_dir)
                collect_file_hashes_from_plist(input_path)
            elif os.path.isdir(input_path):
                _, _, files = next(os.walk(input_path), ([], [], []))
                for f in files:
                    plist_file = os.path.join(input_path, f)
                    LOG.debug("Copying file '{0}' to ZIP assembly dir..."
                              .format(plist_file))
                    shutil.copy(plist_file, report_dir)
                    if f.endswith(".plist"):
                        collect_file_hashes_from_plist(plist_file)

        necessary_hashes = client.getMissingContentHashes(hash_to_file.keys())
        for f, h in file_to_hash.items():
            if h in necessary_hashes:
                target_file = os.path.join(source_dir, f.lstrip('/'))

                try:
                    os.makedirs(os.path.dirname(target_file))
                except os.error:
                    # Directory already exists.
                    pass

                LOG.debug("File contents for '{0}' needed by the server"
                          .format(f))
                shutil.copyfile(f, target_file)

        hashes_fname = "content_hashes.json"
        hashes_fpath = os.path.join(temp_dir, hashes_fname)
        with open(hashes_fpath, "w") as f:
            json.dump(file_to_hash, f)

        with zipfile.ZipFile(zip_file, 'w') as zipf:
            for root, _, files in os.walk(temp_dir):
                for sf in files:
                    f = os.path.join(root, sf)
                    LOG.debug("[ZIP] Writing file '{0}' into mass store ZIP."
                              .format(f))
                    zipf.write(f, f.replace(temp_dir, ''))

        # Compressing .zip file
        with open(zip_file, 'rb') as source:
            compressed = zlib.compress(source.read(),
                                       zlib.Z_BEST_COMPRESSION)

        with open(zip_file, 'wb') as target:
            target.write(compressed)

        LOG.debug("[ZIP] Mass store zip written at '{0}'".format(zip_file))
    finally:
        shutil.rmtree(temp_dir)


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

    # setup connection to the remote server
    client = setup_client(args.host, args.port, '/')

    LOG.debug("Initializing client connecting to " +
              str(args.host) + ":" + str(args.port) + " done.")

    _, zip_file = tempfile.mkstemp('.zip')
    LOG.debug("Will write mass store ZIP to '{0}'...".format(zip_file))

    try:
        assemble_zip(args.input, zip_file, client)
        with open(zip_file, 'rb') as zf:
            b64zip = base64.b64encode(zf.read())

        context = generic_package_context.get_context()

        client.massStoreRun(args.name,
                            context.version,
                            b64zip,
                            args.force)

        LOG.info("Storage finished successfully.")
    except Exception as ex:
        LOG.info("Storage failed: " + str(ex))
    finally:
        os.remove(zip_file)
