// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// core.DivideZero (C, C++, ObjC)
// Check for division by zero.

void test1(int z) {
  if (z == 0)
    int x = 1 / z; // warn
}

void test2() {
  int x = 1;
  int y = x % 0; // warn
}
