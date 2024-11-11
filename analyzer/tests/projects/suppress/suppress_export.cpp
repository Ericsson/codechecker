int foo1()
{
  int *p = 0;

  // codechecker_suppress [all] foo1 simple
  return *p + 2;
}

void foo2()
{
  // codechecker_false_positive [all] foo2 simple
  sizeof(41);
}

void foo3()
{
  // codechecker_intentional [all] foo3 simple
  sizeof(42);
}

void foo4()
{
  // codechecker_confirmed [all] foo4 simple
  sizeof(43);
}

void foo7()
{
  // codechecker_confirmed [sizeof-expression] substring of the checker name
  sizeof(46);
}

int main()
{
  return 0;
}
