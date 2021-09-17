// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

#define SET_PTR_VAR_TO_NULL \
  ptr = 0

void nonFunctionLikeMacroTest() {
  int *ptr;
  SET_PTR_VAR_TO_NULL;
  *ptr = 5; // expected-warning{{Dereference of null pointer}}
}
