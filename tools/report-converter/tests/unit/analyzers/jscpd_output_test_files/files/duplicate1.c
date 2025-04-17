#include <stdio.h>

void greet_and_add1() {
    printf("Hello, User! How are you doing today?\n");
    int a = 5;
    int b = 7;
    int result = a + b;
    printf("The sum of %d and %d is: %d\n", a, b, result);
}

void greet_and_add2() {
    printf("Hello, User! How are you doing today?\n");
    int a = 5;
    int b = 7;
    int result = a + b;
    printf("The sum of %d and %d is: %d\n", a, b, result);
}

void greet_and_add3() {
    printf("Hey there! What's up?\n");
    int a = 5;
    int c = 6;
    int result = a * c;
    printf("The result of %d * %d is: %d\n", a, c, result);
}

int main() {
    greet_and_add1();
    greet_and_add2();
    greet_and_add3();
    return 0;
}
