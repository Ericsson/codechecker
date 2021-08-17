# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Argument parsing related helper classes and functions. """


def add_tls_arguments(parser):
    """
    """
    parser.add_argument('--tlscacert',
                        type=str,
                        metavar='TLS_CACERT',
                        dest="tls_cacert",
                        required=False,
                        help="Trust certs signed only by this CA.")

    parser.add_argument('--tlscert',
                        type=str,
                        metavar='TLS_CERT',
                        dest="tls_cert",
                        required=False,
                        help="Path to TLS certificate file.")

    parser.add_argument('--tlskey',
                        type=str,
                        metavar='TLS_KEY',
                        dest="tls_key",
                        required=False,
                        help="Path to TLS key file.")
