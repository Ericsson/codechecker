# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
suppress handling can be different in packages
baseclass for suppress handler
'''
import abc


class SuppressHandler(object):
    """ suppress handler base class """

    __metaclass__ = abc.ABCMeta

    __suppressfile = None

    @abc.abstractmethod
    def store_suppress_bug_id(self, source_file_path, bug_id, hash_type, comment):
        """ store the suppress bug_id """
        pass

    @abc.abstractmethod
    def remove_suppress_bug_id(self, source_file_path, bug_id, hash_type):
        """ remove the suppress bug_id """
        pass

    @abc.abstractmethod
    def store_suppress_path(self, source_file_path, path, comment):
        """ store the suppress pasth """
        pass

    @property
    def suppress_file(self):
        """" file on the filesystem where the suppress
        data will be written """
        return self.__suppressfile

    @suppress_file.setter
    def suppress_file(self, value):
        """ set the suppress file"""
        self.__suppressfile = value
