#include<stdio.h>
long int multiplyNumbers(int n);
int main() {
    printf("Enter a positive integer: ");
    scanf("%d",&n);
    printf("Factorial of %d = %d", n, multiplyNumbers(n));
    return 0;
}

long int multiplyNumbers(int n) {
    if (n>=1)
        return n*multiplyNumbers(n-1);
    else
        return 1;
}
