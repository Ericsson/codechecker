// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// This file uses header-declared functions to test statistics collection
// from headers. When headers are analyzed, calls to header functions should
// be included in statistics.

#include "statistical_checkers_header.h"

void useHeaderFunctions() {
  char txt[100];
  // Call header functions multiple times - should be counted when headers analyzed
  headerReadFromFile("user_header_a.c", txt);
  headerReadFromFile("user_header_b.c", txt);
  headerReadFromFile("user_header_c.c", txt);
  headerReadFromFile("user_header_d.c", txt);
  headerReadFromFile("user_header_e.c", txt);
  headerReadFromFile("user_header_f.c", txt);
  headerReadFromFile("user_header_g.c", txt);
  headerReadFromFile("user_header_h.c", txt);
  headerReadFromFile("user_header_i.c", txt);
  headerReadFromFile("user_header_j.c", txt);  // 10th call
  headerReadFromFile("user_header_k.c", txt);  // 11th call
  
  headerGetMem();
  headerGetMem();
  headerGetMem();
  headerGetMem();
  headerGetMem();
}
