// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

// This file is to be included in a skip list file.

void skipped_test(int z) {
  if (z == 0)
    int x = 1 / z; // warn
}
