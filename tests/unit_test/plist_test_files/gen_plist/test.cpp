#include <test.h>
#include <iostream>

using namespace std;

void test_func(int base){
    int id;
    id = generate_id(base);
}

char const *p;

void test() {
  char const str[] = "string";
  p = str; // warn
}

int main(){
    int unused; // warn
    int base = 0;
    test_func(base);
    test();
    return 0;
}


