# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Parser for PostgreSQL libpq password file.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import


def _match_field(line, field):
    """
    Return the remaining part of the line in case of matching field,
    otherwise it returns None.
    """

    if line is None or len(line) < 2:
        return None

    if line[0] == '*' and line[1] == ':':
        # Match (star).
        return line[2:]

    escaped = False
    while len(line) > 0:
        if not escaped and line[0] == '\\':
            line = line[1:]
            escaped = True

        if len(line) == 0:
            return None

        if not escaped and line[0] == ':' and len(field) == 0:
            # match
            return line[1:]

        escaped = False
        if len(field) == 0:
            return None
        elif field[0] == line[0]:
            line = line[1:]
            field = field[1:]
        else:
            return None
    return None


def _match_line(line, hostname, port, database, username):
    """
    Tries to match the given line to the given hostname, port, database,
    and username.

    Returns non None on match.
    """

    pw = _match_field(line, hostname)
    pw = _match_field(pw, port)
    pw = _match_field(pw, database)
    pw = _match_field(pw, username)
    if pw is None:
        return pw

    # The password is still escaped.
    escaped = False
    password = ''
    for c in pw:
        if not escaped and c == '\\':
            escaped = True
            continue

        escaped = False
        password += c
    return password


def get_password_from_file(passfile_path, hostname, port, database, username):
    """
    Parser for PostgreSQL libpq password file.

    Returns None on no matching entry, otherwise it returns the password.

    For file format see:
    http://www.postgresql.org/docs/current/static/libpq-pgpass.html
    """

    if len(hostname) == 0 or len(port) == 0 or len(database) == 0 or \
       len(username) == 0:
        return None

    with open(passfile_path, 'r') as passfile:
        for line in passfile:
            pw = _match_line(line.strip(), hostname, port, database, username)
            if pw:
                return pw

    return None
