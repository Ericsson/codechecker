#include <stdio.h>
#include "a.h"

int main()
{
  int a = foo();
  return 1 / 0;
}
