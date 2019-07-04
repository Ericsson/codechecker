// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

#include "skip.h"

int test() {
    int x = null_div(42);
    return x;
}

int test1(int i) {
    int y = i / 0; // warn
    return y;
}

