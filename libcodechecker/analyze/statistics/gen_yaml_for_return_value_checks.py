#!/usr/bin/env python
from __future__ import division
import re
import fileinput

# This script lists
# functions of which the return
# value is mostly checked.

# Sample input line for this script:
# /.../x.c:551:12: warning: Return Value Check:/.../x.c:551:12,parsedate,0


def main():
    gen_yaml()


def gen_yaml():
    print "#"
    print "# UncheckedReturn metadata format 1.0\n"

    THRESHOLD = 0.85
    MIN_OCCURENCE_COUNT = 1
    p = re.compile('.*Return Value Check:.*:[0-9]*:[0-9]*.*,(.*),([0,1])')
    nof_unchecked = dict()
    total = dict()
    for line in fileinput.input():
        m = p.match(line)
        if m:
            func = m.group(1)
            checked = m.group(2)
            if func in total:
                total[func] += 1
                nof_unchecked[func] += int(checked)
            else:
                total[func] = 1
                nof_unchecked[func] = int(checked)

    for key in sorted(total):
        checked_ratio = 1 - nof_unchecked[key]/total[key]
        if (checked_ratio > THRESHOLD and total[key] >= MIN_OCCURENCE_COUNT):
            print "- " + key

if __name__ == "__main__":
    main()
