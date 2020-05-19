// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// core.StackAddressEscape (C)
// Check that addresses of stack memory do not escape the function.

char const *p;

void test1() {
  char const str[] = "string";
  p = str; // warn
}

void* test2() {
  return __builtin_alloca(12); // warn
}

void test3() {
  static int *x;
  int y;
  x = &y; // warn
}
