#include "../include/lib.h"

void foo() {
  int* p = new int(0);
  delete p;
  delete p;
  myDiv(0);
}
