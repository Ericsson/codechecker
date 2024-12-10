#include <stdlib.h>

int main(void) {
    // These commands are intended to test CodeChecker's ability to build-log
    // cross compilations.
    system("gcc -m32 simple.c -o simple32");
    system("gcc -m64 simple.c -o simple64");
    return 0;
} 