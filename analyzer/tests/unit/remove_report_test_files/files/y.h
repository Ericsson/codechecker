#ifndef Y_H
#define Y_H

#define SET_PTR_VAR_TO_NULL \
  ptr = 0

void macroExpansion() {
  int *ptr;
  SET_PTR_VAR_TO_NULL;
  *ptr = 5; // expected-warning{{Dereference of null pointer}}
}

#endif
