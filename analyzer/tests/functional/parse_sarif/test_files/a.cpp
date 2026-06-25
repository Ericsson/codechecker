int main()
{
  int x;
  // codechecker_false_positive [DeadStores] testing suppression via source code comment
  x = 1;

  // Suppressed by config file.
  return 1 / 0;
}
