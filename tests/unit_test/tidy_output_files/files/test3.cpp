#include "test3.hh"

int main(int argc, const char** /*argv*/) {
  int* x = 0;
  
  if (foo(argc > 3)) {
    bar(x);
  }
  
  return 0;
}
