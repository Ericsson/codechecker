#include "inc.h"

void direct(void)
{
  // // Defect example:
  // int x = 0;
  // int y = 1 / x;
}


int main(void)
{
  direct();
  int result = ctu(0);
  transitive();
  return result;
}
