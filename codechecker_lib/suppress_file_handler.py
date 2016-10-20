# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""" Suppress file format.

# This is the old format.
123324353456463442341242342343#1 || bug hash comment

# This is the new format.
123324353456463442341242342343#1 || filename || bug hash comment

After removing the hash_value_type the generated format is:
123324353456463442341242342343 || filename || bug hash comment

For backward compatibility the hash_value_type is an optional filed.
"""

import abc
import codecs
import os
import re

from codechecker_lib import logger
from codechecker_lib import suppress_handler

LOG = logger.get_new_logger('SUPPRESS_FILE_HANDLER')

COMMENT_SEPARATOR = '||'
HASH_TYPE_SEPARATOR = '#'


class SuppressHandler(object):
    """ Suppress handler base class. """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def store_suppress_bug_id(self,
                              bug_id,
                              file_name,
                              comment):
        """ Store the suppress bug_id. """
        pass

    @abc.abstractmethod
    def remove_suppress_bug_id(self,
                               bug_id,
                               file_name):
        """ Remove the suppress bug_id. """
        pass


class SuppressFileHandler(SuppressHandler):

    old_format_pattern = r"^(?P<bug_hash>[\d\w]{32})" \
        r"(\#(?P<bug_hash_type>\d))?\s*\|\|\s*(?P<comment>[^\|]*)$"
    old_format = re.compile(old_format_pattern, re.UNICODE)

    new_format_pattern = r"^(?P<bug_hash>[\d\w]{32})"\
        r"(\#(?P<bug_hash_type>\d))?\s*\|\|\s*(?P<file_name>[^\\\|]+)" \
        r"\s*\|\|\s*(?P<comment>[^\|]*)$"
    new_format = re.compile(new_format_pattern, re.UNICODE)

    __suppress_file = None

    def __init__(self, suppress_file=None):
        self.__suppress_file = suppress_file
        super(SuppressFileHandler, self).__init__()

    def store_suppress_bug_id(self, bug_id, file_name, comment):

        if self.__suppress_file is None:
            return False

        ret = self.__write_to_suppress_file(self.__suppress_file,
                                            bug_id,
                                            file_name,
                                            comment)
        return ret

    def remove_suppress_bug_id(self, bug_id, file_name):

        if self.suppress_file is None:
            return False

        ret = self.__remove_from_suppress_file(
            self.__suppress_file,
            bug_id,
            file_name)
        return ret

    @property
    def suppress_file(self):
        """" File on the filesystem where the suppress
        data will be written. """
        return self.__suppress_file

    @suppress_file.setter
    def suppress_file(self, value):
        """ Set the suppress file. """
        self.__suppress_file = value

    @staticmethod
    def get_suppress_data_from_file(suppress_file):
        if os.path.exists(suppress_file):
            with codecs.open(suppress_file, 'r', 'UTF-8') as s_file:
                return SuppressFileHandler.get_suppress_data(s_file)
        else:
            return []

    @classmethod
    def get_suppress_data(cls, suppress_file):
        """
        Process a file object for suppress information.
        """

        suppress_data = []

        for line in suppress_file:

            new_format_match = re.match(cls.new_format, line.strip())
            if new_format_match:
                LOG.debug('Match for new suppress entry format:')
                new_format_match = new_format_match.groupdict()
                LOG.debug(new_format_match)
                suppress_data.append((new_format_match['bug_hash'],
                                      new_format_match['file_name'],
                                      new_format_match['comment']))
                continue

            old_format_match = re.match(cls.old_format, line.strip())
            if old_format_match:
                LOG.debug('Match for old suppress entry format:')
                old_format_match = old_format_match.groupdict()
                LOG.debug(old_format_match)
                suppress_data.append((old_format_match['bug_hash'],
                                      u'',  # empty file name
                                      old_format_match['comment']))
                continue

            if line.strip() != '':
                LOG.warning('Malformed suppress line: ' + line)

        return suppress_data

    def __write_to_suppress_file(self, suppress_file, value, file_name,
                                 comment=''):

        LOG.debug('Processing suppress file: ' + suppress_file)

        try:
            suppress_data = \
                SuppressFileHandler.get_suppress_data_from_file(suppress_file)

            if not os.stat(suppress_file)[6] == 0:
                # File is not empty.

                res = filter(lambda x: (x[0] == value and x[1] == file_name) or
                                       (x[0] == value and x[1] == ''),
                             suppress_data)

                if res:
                    LOG.debug("Already found in\n %s" % suppress_file)
                    return True

            comment = comment.decode('UTF-8')

            with codecs.open(suppress_file, 'a', 'UTF-8') as s_file:
                s_file.write(value + COMMENT_SEPARATOR +
                             file_name + COMMENT_SEPARATOR +
                             comment + '\n')

            return True

        except Exception as ex:
            LOG.error(str(ex))
            LOG.error("Failed to write: %s" % suppress_file)
            return False

    def __remove_from_suppress_file(self, suppress_file, value, file_name):
        """
        Remove suppress information from the suppress file.
        Old and new format is supported.
        """

        LOG.debug('Removing ' + value + ' from \n' + suppress_file)

        # remove patterns
        old_format_remove_pattern = r"^" + value + \
            r"(\#\d)?\s*\|\|\s*(?P<comment>[^\|]*)$"
        old_format_remove = re.compile(old_format_remove_pattern, re.UNICODE)

        new_format_remove_pattern = r"^" + value + r"(\#d)?\s*\|\|\s*" + \
            file_name + r"\s*\|\|\s*(?P<comment>[^\|]*)$"
        new_format_remove = re.compile(new_format_remove_pattern, re.UNICODE)

        def check_for_match(line):
            """
            Check if the line matches the new or old format.
            Match for new format first because it is more specific.
            """
            line = line.strip()
            if re.match(new_format_remove, line.strip()):
                return False
            if re.match(old_format_remove, line.strip()):
                return False
            else:
                return True

        try:
            with codecs.open(suppress_file, 'r+', 'UTF-8') as s_file:

                lines = s_file.readlines()

                # Filter out lines which should be removed.
                lines = filter(lambda line: check_for_match(line), lines)

                s_file.seek(0)
                s_file.truncate()
                s_file.writelines(lines)

            return True

        except Exception as ex:
            LOG.error(str(ex))
            LOG.error("Failed to write: %s" % suppress_file)
            return False
