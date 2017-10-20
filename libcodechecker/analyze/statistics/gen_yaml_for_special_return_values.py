#!/usr/bin/env python
from __future__ import division
import re
import fileinput

# This script lists
# functions of which the return
# value is checked for negative
# (integers) or null (pointers).

# Sample input line for this script:
# /.../x.c:551:12: warning: Special Return Value:/.../x.c:551:12,parsedate,0,0


def main():
    gen_yaml()


def gen_yaml():
    print "#"
    print "# SpecialReturn metadata format 1.0\n"

    THRESHOLD = 0.85
    MIN_OCCURENCE_COUNT = 1
    p = re.compile('.*Special Return Value:.*:[0-9]*:[0-9]*.*,(.*),([0,1]),([0,1])')
    nof_negative = dict()
    nof_null = dict()
    total = dict()
    for line in fileinput.input():
        m = p.match(line)
        if m:
            func = m.group(1)
            ret_negative = m.group(2)
            ret_null = m.group(3)
            if func in total:
                total[func] += 1
                nof_negative[func] += int(ret_negative)
                nof_null[func] += int(ret_null)
            else:
                total[func] = 1
                nof_negative[func] = int(ret_negative)
                nof_null[func] = int(ret_null)

    for key in sorted(total):
        negative_ratio = nof_negative[key]/total[key]
        null_ratio = nof_null[key]/total[key]
        if (negative_ratio > THRESHOLD and total[key] >= MIN_OCCURENCE_COUNT):
            print "{name: " + key + ", relation: LT, value: 0}"
        if (null_ratio > THRESHOLD and total[key] >= MIN_OCCURENCE_COUNT):
            print "{name: " + key + ", relation: EQ, value: 0}"

if __name__ == "__main__":
    main()
