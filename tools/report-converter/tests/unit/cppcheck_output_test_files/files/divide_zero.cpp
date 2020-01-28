// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

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
