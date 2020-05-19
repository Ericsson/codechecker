// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// core.NullDereference (C, C++, ObjC)
// Check for dereferences of null pointers.

void test1(int *p) {
  if (p)
    return;

  int x = p[0]; // warn
}

void test2(int *p) {
  if (!p)
    *p = 0; // warn
}

class C {
public:
  int x;
};

void test3() {
  C *pc = 0;
  int k = pc->x; // warn
}
