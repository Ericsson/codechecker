#ifndef X_H
#define X_H

float foo(int x) {
  return 1 / x;
}

long bar1(long a, long b, long c, long d) {
  c = a - b;
  c = c / d * a;
  d = b * b - c; // expected-warning{{Potential copy-paste error; did you really mean to use 'b' here?}}
  return d;
}

#endif
