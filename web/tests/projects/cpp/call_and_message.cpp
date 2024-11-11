// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// core.CallAndMessage (C, C++, ObjC)
// Check for logical errors for function calls and Objective-C message
// expressions (e.g., uninitialized arguments, null function pointers).

struct S {
    int x;
};

void f(struct S s);

void test1() {
  struct S s;
  // insert_suppress_here
  f(s); // warn: passed-by-value arg contain uninitialized data
}

void test2() {
  void (*foo)(void);
  foo(); // warn: function pointer is uninitialized
}

void test3() {
  void (*foo)(void);
  foo = 0;
  foo(); // warn: function pointer is null
}

class C {
public:
  void f();
};

void test4() {
  C *pc;
  pc->f(); // warn: object pointer is uninitialized
}

void test5() {
  C *pc = 0;
  pc->f(); // warn: object pointer is null <- non breaking space here save the file in latin1 (ISO-8895-1)
}
