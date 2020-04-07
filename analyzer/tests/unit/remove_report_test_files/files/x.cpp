#include "x.h"
#include "y.h"
#include "empty.h"

long bar2(long a, long b, long c, long d) {
  c = a - b;
  c = c / d * a;
  d = c * b - c; // expected-note{{Similar code using 'c' here}} \
                 // expected-warning{{Potential copy-paste error; did you really mean to use 'c' here?}}
  return d;
}

void divideByZero(int z) {
  if (z == 0)
    int x = 1 / z; // warn
}

int main() {
  foo(0);
}
