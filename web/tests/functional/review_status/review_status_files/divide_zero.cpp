// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// core.DivideZero (C, C++, ObjC)
// Check for division by zero.

int test1(int z) {
  if (z == 0){
    // codechecker_intentional [core.DivideZero] intentional divide by zero here
    int x = 1 / z; // warn
    return x;
  }
}

int test2() {
  int x = 1;
  // codechecker_intentional [core.DivideZero] intentional divide by zero here
  int y = x % 0; // warn
  return y;
}
