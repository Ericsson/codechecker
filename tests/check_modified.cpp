#include <stdlib.h>

#define ZERO 0

int getNull(int a){return a ? 0 : 1;}

int getInput() __attribute__((notzero));
void test(int b) {
  int a, c;
  double *d;
  switch (b) {
  case1:
    a = b / 0;
    break;
  case2:
    a = b / ZERO;
    break;
  case 3:
    d = (double *)malloc(sizeof(d));
    free(d);
    break;
  case4:
    c = b - 4;
    a = b / c;
    break;
  case 5:
    if(getNull(b) != 0) {
      a = b / getNull(b);
    }
    break;
  case 6:
    a = b / getInput();
    break;
  };
}