// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

int main() {

  int x = 1;
  int y = x/1; // Value stored is never read.

  return 0;
}
