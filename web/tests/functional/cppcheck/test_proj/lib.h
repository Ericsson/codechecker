// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

// core.DivideZero (C, C++, ObjC)
// Check for division by zero.

void div(int x) {
  int y = x % 0; // warn
}
