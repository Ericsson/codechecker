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

void foo5()
{
  // codechecker_suppress [all] foo5 all
  // codechecker_confirmed [misc-sizeof-expression] foo5 simple
  sizeof(44);
}

void foo6()
{
  // codechecker_suppress [all, misc-sizeof-expression] foo6 multiple
  // codechecker_confirmed [misc-sizeof-expression] foo6 simple
  sizeof(45);
}

int main()
{
  return 0;
}
