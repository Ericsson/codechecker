// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// core.NullDereference (C, C++, ObjC)
// Check for dereferences of null pointers.

int main()
{
  int *p = 0;
  return *p + 4;
}