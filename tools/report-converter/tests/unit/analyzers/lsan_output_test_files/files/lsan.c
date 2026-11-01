// COMPILE: clang -fsanitize=address -fomit-frame-pointer -g lsan2.c

#include <stdlib.h>
void *p;
int main()
{
    p = malloc(7);
    p = 0; // The memory is leaked here.
    return 0;
}
