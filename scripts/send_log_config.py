#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import argparse
import json
import socket
import struct


parser = argparse.ArgumentParser(
        description="""
Send a python log config (json) to a port where a logging process listens.

Further details about the log configuration format and usage can be found here:
https://docs.python.org/2/library/logging.config.html """,
        formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-c', action="store", required="True",
                    dest="config_file",
                    help="Log configuration in json format.")

parser.add_argument('-p', action="store", required="True",
                    dest="port", type=int,
                    help="Port number of the logger server.")

args = parser.parse_args()

try:
    with open(args.config_file, 'rb') as cf:
        log_config = cf.read()

        # Just a simple check for valid json before sending
        json.loads(log_config)

        data_to_send = log_config

    host = 'localhost'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print('Connecting to {0}:{1} ...'.format(host, args.port))
    s.connect((host, args.port))
    print('Connection done.')

    print('Sending config ...')
    s.send(struct.pack('>L', len(data_to_send)))
    s.send(data_to_send)
    s.close()
    print('Sending config done.')

except IOError as ex:
    print("Failed to read config file" + args.config_file)
    print(ex)
    print(ex.message)

except ValueError as ex:
    print("Wrong config file format.")
    print(ex)
    print(ex.message)
