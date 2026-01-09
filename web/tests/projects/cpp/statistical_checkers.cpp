// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// core.StackAddressEscape (C)
// Check that addresses of stack memory do not escape the function.


/* Test file for the statistical countinf feature
/* for alpha.ericsson.statisticscollector.ReturnValueCheck
 * alpha.ericsson.statisticscollector.SpecialReturnValue
 */

#include "statistical_checkers_header.h"

int readFromFile(const char* fileName, char *text){
  if (!fileName) //return with error if
    return -1;
  else{
  }
}

int *getMem();

// Forward declaration
void testHeaderFunctions();

void testUncheckedReturn(){
  char txt[100];
  int err=readFromFile("a.c",txt);
  if (err==-1)
    return;
  readFromFile("k.c",txt); //warning: the return value of readFromFile is usually checked
  if (readFromFile("b.c",txt) == 0)
    return;
  if (readFromFile("c.c",txt)==-2)
      return;
  if (readFromFile("d.c",txt)==-1)
      return;
  if (readFromFile("e.c",txt)==-1)
      return;
  if (readFromFile("f.c",txt)==-1)
      return;
  if (readFromFile("g.c",txt)==-1)
      return;
  if (readFromFile("h.c",txt)==-1)
      return;
  if (readFromFile("i.c",txt)==-1)
      return;
  readFromFile("j.c",txt); //warning: the return value of readFromFile is usually checked
  
  // Also call header functions to ensure they're analyzed
  testHeaderFunctions();
}


int testSpecialReturn(){
  if (getMem()!=0)
    return 0;
  if (!getMem())
    return 0;
  if (!getMem())
    return 0;
  return *getMem();


}

// Test functions that use header-declared functions
void testHeaderFunctions() {
  char txt[100];
  // Call header function multiple times - should be counted in statistics when headers are analyzed
  // Need at least 10 calls to meet default minimum sample count threshold
  headerReadFromFile("header_a.c", txt);
  headerReadFromFile("header_b.c", txt);
  headerReadFromFile("header_c.c", txt);
  headerReadFromFile("header_d.c", txt);
  headerReadFromFile("header_e.c", txt);
  headerReadFromFile("header_f.c", txt);
  headerReadFromFile("header_g.c", txt);
  headerReadFromFile("header_h.c", txt);
  headerReadFromFile("header_i.c", txt);
  headerReadFromFile("header_j.c", txt);  // 10th call to meet threshold
  // Unchecked return - should generate warning when statistics are used
  headerReadFromFile("header_k.c", txt);
  
  if (headerGetMem() != 0)
    return;
  if (!headerGetMem())
    return;
  headerGetMem(); // Unchecked - should generate warning
  headerGetMem(); // More calls for statistics
  headerGetMem();
}
