#include <stdio.h>

int main(int argc, char** argv)
{
  int* a = new int[10];
  a[5] = 0;
  if (a[argc])
    printf("xx\n");
  return 0;
}
