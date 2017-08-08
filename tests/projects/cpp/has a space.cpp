// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

// core.NullDereference (C, C++, ObjC)
// Check for dereferences of null pointers.

int main()
{
  int *p = 0;
  return *p + 4;
}