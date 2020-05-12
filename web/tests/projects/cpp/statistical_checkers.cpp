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

int readFromFile(const char* fileName, char *text){
  if (!fileName) //return with error if
    return -1;
  else{
  }
}

int *getMem();

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
