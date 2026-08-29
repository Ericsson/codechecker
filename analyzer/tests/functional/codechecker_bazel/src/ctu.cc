// This is an example of CTU (Cross-Translation Unit) analysis
// Test manually with and without --ctu option:
//   CodeChecker check --ctu -b "gcc -Itest/inc test/src/ctu.cc test/src/lib.cc test/src/fail.cc"
int ctu(int c)
{
  // CTU example (c is being passed from main)
  int result = 1 / c;  // CTU example
  return result;
}
