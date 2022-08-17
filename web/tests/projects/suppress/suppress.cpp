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

void foo8()
{
  sizeof(47);
}

void foo9()
{
  // codechecker_confirmed [bugprone-sizeof-expression] Has a source code comment.
  sizeof(48);

  // codechecker_intentional [bugprone-sizeof-expression] Has a different source code comment.
  sizeof(48);

  sizeof(48);
}

int main()
{
  return 0;
}
