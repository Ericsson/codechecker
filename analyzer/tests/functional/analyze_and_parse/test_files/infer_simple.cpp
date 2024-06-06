#include <stdlib.h>

void test() {
  int *s = NULL;
  *s = 42;
  // https://fbinfer.com/docs/all-issue-types#null_dereference
}