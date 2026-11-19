# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test the conversion of datetimes to and from API date strings. """


from datetime import datetime, timedelta, timezone
import os
import time
import unittest

from codechecker_server.api.common import api_str_to_datetime, \
    datetime_to_api_str


class ApiDatetimeTestCase(unittest.TestCase):
    """
    The server stores naive datetimes in its local timezone. The API must
    send them with an explicit UTC offset and accept both the old offset-less
    format and the new one.
    """

    def setUp(self):
        self.__old_tz = os.environ.get('TZ')
        os.environ['TZ'] = 'Europe/Budapest'
        time.tzset()

    def tearDown(self):
        if self.__old_tz is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = self.__old_tz
        time.tzset()

    def test_none(self):
        self.assertIsNone(datetime_to_api_str(None))

    def test_naive_summer_time(self):
        self.assertEqual(
            datetime_to_api_str(datetime(2024, 7, 1, 12, 0, 0, 123456)),
            '2024-07-01 12:00:00.123456+02:00')

    def test_naive_winter_time(self):
        self.assertEqual(
            datetime_to_api_str(datetime(2024, 1, 15, 12, 0, 0, 123456)),
            '2024-01-15 12:00:00.123456+01:00')

    def test_microseconds_always_present(self):
        self.assertEqual(
            datetime_to_api_str(datetime(2024, 7, 1, 12, 0, 0)),
            '2024-07-01 12:00:00.000000+02:00')

    def test_aware_value_keeps_its_offset(self):
        self.assertEqual(
            datetime_to_api_str(
                datetime(2024, 7, 1, 10, 0, 0, tzinfo=timezone.utc)),
            '2024-07-01 10:00:00.000000+00:00')

    def test_parse_legacy_format(self):
        self.assertEqual(
            api_str_to_datetime('2024-07-01 12:00:00.123456'),
            datetime(2024, 7, 1, 12, 0, 0, 123456))

    def test_parse_legacy_format_without_microseconds(self):
        # Old servers used str(), which drops the fraction when it is zero.
        self.assertEqual(
            api_str_to_datetime('2024-07-01 12:00:00'),
            datetime(2024, 7, 1, 12, 0, 0))

    def test_parse_offset_to_server_local(self):
        # The result is naive and in the server's timezone, like DB values.
        self.assertEqual(
            api_str_to_datetime('2024-07-01 10:00:00.000000+00:00'),
            datetime(2024, 7, 1, 12, 0, 0))
        self.assertEqual(
            api_str_to_datetime('2024-01-15 06:30:00.000001-05:00'),
            datetime(2024, 1, 15, 12, 30, 0, 1))

    def test_round_trip(self):
        dt = datetime(2024, 3, 31, 1, 59, 59, 999999)
        self.assertEqual(api_str_to_datetime(datetime_to_api_str(dt)), dt)
        dt = dt + timedelta(hours=2)
        self.assertEqual(api_str_to_datetime(datetime_to_api_str(dt)), dt)
