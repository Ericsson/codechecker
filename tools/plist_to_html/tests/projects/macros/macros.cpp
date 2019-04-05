// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

#define SET_PTR_VAR_TO_NULL \
  ptr = 0

void nonFunctionLikeMacroTest() {
  int *ptr;
  SET_PTR_VAR_TO_NULL;
  *ptr = 5; // expected-warning{{Dereference of null pointer}}
}
