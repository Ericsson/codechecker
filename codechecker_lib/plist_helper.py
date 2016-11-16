# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
""" This file contains some workaround for CodeChecker
to work with older clang versions. It is for demonstration purposes only.
The names, hashes will change after switching to a newer clang version.
"""

import hashlib
import linecache
import os
import re

from codechecker_lib import logger

LOG = logger.get_new_logger('PLIST_HELPER')


def gen_bug_hash(bug):
    line_content = linecache.getline(bug.file_path, bug.from_line)
    if line_content == '' and not os.path.isfile(bug.file_path):
        LOG.debug('%s does not exists!' % bug.file_path)

    file_name = os.path.basename(bug.file_path)
    l = [file_name, bug.checker_name, bug.msg, line_content,
         str(bug.from_col), str(bug.until_col)]
    for p in bug.paths():
        l.append(str(p.start_pos.col))
        l.append(str(p.end_pos.col))
    string_to_hash = '|||'.join(l)
    return hashlib.md5(string_to_hash.encode()).hexdigest()


def levenshtein(a, b):  # http://hetland.org/coding/python/levenshtein.py
    """"Calculates the Levenshtein distance between a and b."""
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space.
        a, b = b, a
        n, m = m, n

    current = range(n+1)
    for i in range(1, m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1, n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)

    return current[n]


def get_check_name(current_msg):
    # Clean message from variable and class name.
    clean_msg = re.sub(r"'.*?'", '', current_msg)

    closest_msg = ''
    min_dist = len(clean_msg) // 4

    for msg in checker_message_map.keys():
        tmp_dist = levenshtein(clean_msg, msg)
        if tmp_dist < min_dist:
            closest_msg = msg
            min_dist = tmp_dist

    return checker_message_map[closest_msg]


# This map needs extending.
checker_message_map = \
    {
        "": "NOT FOUND",

        "Access out-of-bound array element (buffer overflow)":

        "alpha.security.ArrayBound",

        "Address of stack memory associated with local variable  returned to "
        "caller": "core.StackAddressEscape",

        "Argument to  is uninitialized": "core.CallAndMessage",

        "Argument to free() is the address of the global variable , which is "
        "not memory allocated by malloc()": "alpha.unix.MallocWithAnnotations",

        "Argument to free() is the address of the local variable , which is "
        "not memory allocated by malloc()": "alpha.unix.MallocWithAnnotations",

        "Assigned value is garbage or undefined": "core.uninitialized.Assign",

        "Attempt to free released memory": "alpha.unix.MallocWithAnnotations",

        "Branch condition evaluates to a garbage value":
        "core.uninitialized.Branch",

        "Call to function  is extremely insecure as it can always result in a "
        "buffer overflow": "security.insecureAPI.gets",

        "Call to function  is insecure as it always creates or uses insecure "
        "temporary file.  Use  instead": "security.insecureAPI.mktemp",

        "Call to function  is insecure as it does not provide bounding of the "
        "memory buffer. Replace unbounded copy functions with analogous "
        "functions that support length arguments such as . CWE-119":
        "security.insecureAPI.strcpy",

        "Cast a region whose size is not a multiple of the destination "
        "type size": "alpha.core.CastSize",

        "Dereference of null pointer (loaded from variable )":
        "core.NullDereference",

        "Dereference of undefined pointer value": "core.NullDereference",

        "Division by zero": "core.DivideZero",

        "Function call argument is a pointer to uninitialized value":
        "core.CallAndMessage",

        "Function call argument is an uninitialized value":
        "core.CallAndMessage",

        "identical expressions on both sides of logical operator":
        "alpha.core.IdenticalExpr",

        "Memory allocated by  should be deallocated by , not ":
        "unix.MismatchedDeallocator",

        "Memory allocated by  should be deallocated by , not free()":
        "unix.MismatchedDeallocator",

        "No call of chdir(\"/\") immediately after chroot":
        "alpha.unix.Chroot",

        "Opened File never closed. Potential Resource leak":
        "alpha.unix.Stream",

        "Potential leak of memory pointed to by ": "cplusplus.NewDelete",

        "Potential memory leak": "cplusplus.NewDelete",

        "Result of  is converted to a pointer of type , which is incompatible "
        "with sizeof operand type ": "unix.MallocSizeof",

        "Size argument is greater than the length of the destination buffer":
        "alpha.unix.cstring.OutOfBounds",

        "The code calls sizeof() on a pointer type. This can produce an "
        "unexpected result": "alpha.core.SizeofPtr",

        "the computation of the size of the memory allocation may overflow":
        "alpha.security.MallocOverflow",

        "The left operand of  is a garbage value":
        "core.UndefinedBinaryOperatorResult",

        "The right operand of  is a garbage value":
        "core.UndefinedBinaryOperatorResult",

        "This statement is never executed": "alpha.deadcode.UnreachableCode",
        "Undefined or garbage value returned to caller":

        "core.uninitialized.UndefReturn",
        "Use of memory after it is freed": "alpha.unix.MallocWithAnnotations",

        "Value stored to  during its initialization is never read":
        "deadcode.DeadStores",

        "Value stored to  is never read": "deadcode.DeadStores"
    }
