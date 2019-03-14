// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

void log();

int max(int a, int b) { // expected-warning{{Duplicate code detected}}
  log();
  if (a > b)
    return a;
  return b;
}

int maxClone(int a, int b) { // expected-note{{Similar code here}}
  log();
  if (a > b)
    return a;
  return b;
}
