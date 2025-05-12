#include <stdio.h>

void greet_and_add3() {
    printf("Hey there! What's up?\n");
    int a = 5;
    int c = 6;
    int result = a * c;
    printf("The result of %d * %d is: %d\n", a, c, result);
}

int main() {
    greet_and_add3();
    return 0;
}
