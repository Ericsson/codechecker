// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

#include "skip.h"

int test() {
    int x = null_div(42);
    return x;
}

int test1(int i) {
    int y = i / 0; // warn
    return y;
}

