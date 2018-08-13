# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
'CodeChecker store' parses a list of analysis results and stores them in the
database.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import base64
import errno
import json
import os
import sys
import tempfile
import zipfile
import zlib

from shared.ttypes import Permission, RequestFailed, ErrorCode

from libcodechecker import logger
from libcodechecker import generic_package_context
from libcodechecker import host_check
from libcodechecker import util
from libcodechecker.analyze import plist_parser
from libcodechecker.libclient import client as libclient
from libcodechecker.output_formatters import twodim_to_str
from libcodechecker.util import sizeof_fmt
from libcodechecker.util import split_product_url


LOG = logger.get_logger('system')

MAX_UPLOAD_SIZE = 1 * 1024 * 1024 * 1024  # 1GiB


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

    parser.add_argument('--tag',
                        type=str,
                        dest="tag",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="A uniques identifier for this individual store "
                             "of results in the run's history.")

    parser.add_argument('--trim-path-prefix',
                        type=str,
                        nargs='*',
                        dest="trim_path_prefix",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Removes leading path from files which will be "
                             "stored. So if you have /a/b/c/x.cpp and "
                             "/a/b/c/y.cpp then by removing \"/a/b/\" prefix "
                             "will store files like c/x.cpp and c/y.cpp. "
                             "If multiple prefix is given, the longest match "
                             "will be removed.")

    parser.add_argument('-f', '--force',
                        dest="force",
                        default=argparse.SUPPRESS,
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
        "store the results. This server must be running and listening, and "
        "the given product must exist prior to the 'store' command being ran.")

    server_args.add_argument('--url',
                             type=str,
                             metavar='PRODUCT_URL',
                             dest="product_url",
                             default="localhost:8001/Default",
                             required=False,
                             help="The URL of the product to store the "
                                  "results for, in the format of "
                                  "'[http[s]://]host:port/Endpoint'.")

    logger.add_verbose_arguments(parser)
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
    hash_to_file = {}
    # There can be files with same hash,
    # but different path.
    file_to_hash = {}
    file_to_mtime = {}
    missing_source_files = set()

    def collect_file_hashes_from_plist(plist_file):
        """
        Collects file content hashes and last modification times of files which
        can be found in the given plist file.

        :returns List of file paths which are in the processed plist file but
        missing from the user's disk.
        """
        missing_files = []
        try:
            files, _ = plist_parser.parse_plist(plist_file)

            for f in files:
                if not os.path.isfile(f):
                    missing_files.append(f)
                    missing_source_files.add(f)
                    continue

                content_hash = util.get_file_content_hash(f)
                hash_to_file[content_hash] = f
                file_to_hash[f] = content_hash
                file_to_mtime[f] = util.get_last_mod_time(f)

            return missing_files
        except Exception as ex:
            LOG.error('Parsing the plist failed: ' + str(ex))

    plist_report_files = []

    changed_files = set()
    for input_path in inputs:
        input_path = os.path.abspath(input_path)

        if not os.path.exists(input_path):
            raise OSError(errno.ENOENT,
                          "Input path does not exist", input_path)

        if os.path.isfile(input_path):
            files = [input_path]
        else:
            _, _, files = next(os.walk(input_path), ([], [], []))

        for f in files:
            plist_file = os.path.join(input_path, f)
            if f.endswith(".plist"):
                missing_files = collect_file_hashes_from_plist(plist_file)
                if not missing_files:
                    LOG.debug(
                        "Copying file '{0}' to ZIP assembly dir..."
                        .format(plist_file))
                    plist_report_files.append(os.path.join(input_path, f))
                else:
                    LOG.warning("Skipping '%s' because it refers "
                                "the following missing source files: %s",
                                plist_file, missing_files)
            elif f == 'metadata.json':
                plist_report_files.append(os.path.join(input_path, f))
            elif f == 'skip_file':
                plist_report_files.append(os.path.join(input_path, f))

            plist_mtime = util.get_last_mod_time(plist_file)

            for k, v in file_to_mtime.items():
                if v > plist_mtime:
                    changed_files.add(k)

    if changed_files:
        changed_files = '\n'.join([' - ' + f for f in changed_files])
        LOG.warning("The following source file contents changed since the "
                    "latest analysis:\n{0}\nPlease analyze your project "
                    "again to update the reports!".format(changed_files))
        sys.exit(1)

    with zipfile.ZipFile(zip_file, 'a', allowZip64=True) as zipf:
        for pl in plist_report_files:
            _, plist_filename = os.path.split(pl)
            zip_target = os.path.join('reports', plist_filename)
            zipf.write(pl, zip_target)

        if len(hash_to_file) == 0:
            LOG.warning("There is no report to store. After uploading these "
                        "results the previous reports become resolved.")

        file_hashes = hash_to_file.keys()
        necessary_hashes = client.getMissingContentHashes(file_hashes) \
            if file_hashes else []

        for f, h in file_to_hash.items():
            if h in necessary_hashes:
                LOG.debug("File contents for '{0}' needed by the server"
                          .format(f))

                zipf.write(f, os.path.join('root', f.lstrip('/')))

        zipf.writestr('content_hashes.json', json.dumps(file_to_hash))

    # Compressing .zip file
    with open(zip_file, 'rb') as source:
        compressed = zlib.compress(source.read(),
                                   zlib.Z_BEST_COMPRESSION)

    with open(zip_file, 'wb') as target:
        target.write(compressed)

    LOG.debug("[ZIP] Mass store zip written at '{0}'".format(zip_file))

    if missing_source_files:
        LOG.warning("Missing source files: \n%s", '\n'.join(
            map(lambda f_: " - " + f_, missing_source_files)))


def main(args):
    """
    Store the defect results in the specified input list as bug reports in the
    database.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

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

    if 'force' in args:
        LOG.info("argument --force was specified: the run with name '" +
                 args.name + "' will be deleted.")

    protocol, host, port, product_name = split_product_url(args.product_url)

    # Before any transmission happens, check if we have the PRODUCT_STORE
    # permission to prevent a possibly long ZIP operation only to get an
    # error later on.
    product_client = libclient.setup_product_client(protocol,
                                                    host, port, product_name)
    product_id = product_client.getCurrentProduct().id

    auth_client, _ = libclient.setup_auth_client(protocol, host, port)
    has_perm = libclient.check_permission(
        auth_client, Permission.PRODUCT_STORE, {'productID': product_id})
    if not has_perm:
        LOG.error("You are not authorised to store analysis results in "
                  "product '{0}'".format(product_name))
        sys.exit(1)

    # Setup connection to the remote server.
    client = libclient.setup_client(args.product_url, product_client=False)

    LOG.debug("Initializing client connecting to {0}:{1}/{2} done."
              .format(host, port, product_name))

    _, zip_file = tempfile.mkstemp('.zip')
    LOG.debug("Will write mass store ZIP to '{0}'...".format(zip_file))

    try:
        assemble_zip(args.input, zip_file, client)

        if os.stat(zip_file).st_size > MAX_UPLOAD_SIZE:
            LOG.error("The result list to upload is too big (max: {})."
                      .format(sizeof_fmt(MAX_UPLOAD_SIZE)))
            sys.exit(1)

        with open(zip_file, 'rb') as zf:
            b64zip = base64.b64encode(zf.read())

        context = generic_package_context.get_context()

        trim_path_prefixes = args.trim_path_prefix if \
            'trim_path_prefix' in args else None

        client.massStoreRun(args.name,
                            args.tag if 'tag' in args else None,
                            str(context.version),
                            b64zip,
                            'force' in args,
                            trim_path_prefixes)

        LOG.info("Storage finished successfully.")
    except RequestFailed as reqfail:
        if reqfail.errorCode == ErrorCode.SOURCE_FILE:
            header = ['File', 'Line', 'Checker name']
            table = twodim_to_str('table',
                                  header,
                                  [c.split('|') for c in reqfail.extraInfo])
            LOG.warning("Setting the review statuses for some reports failed "
                        "because of non valid source code comments: "
                        "{0}\n {1}".format(reqfail.message, table))
        sys.exit(1)
    except Exception as ex:
        LOG.info("Storage failed: " + str(ex))
        sys.exit(1)
    finally:
        os.remove(zip_file)
