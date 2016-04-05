// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

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
