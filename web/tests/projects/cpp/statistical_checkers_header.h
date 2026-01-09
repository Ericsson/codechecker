// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

#ifndef STATISTICAL_CHECKERS_HEADER_H
#define STATISTICAL_CHECKERS_HEADER_H

// Function definitions in header file for statistics collection testing
// These are defined in the header (not inline) so they're only analyzed when headers are analyzed
// Note: Multiple definitions are OK per ODR if they're identical
int headerReadFromFile(const char* fileName, char *text) {
  if (!fileName)
    return -1;
  return 0;
}

int *headerGetMem() {
  static int mem = 0;
  return &mem;
}

void headerTestUncheckedReturn();

int headerTestSpecialReturn();

#endif  // STATISTICAL_CHECKERS_HEADER_H
