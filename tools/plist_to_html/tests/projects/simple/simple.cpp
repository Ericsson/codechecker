// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

void test(int z) {
  if (z == 0)
    int x = 1 / z; // warn
}
