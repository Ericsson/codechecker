#include <iostream>

// Unused function declaration
void unusedFunction();

// Unused variable
int unusedVar = 42;

int main() {
    // Uninitialized pointer
    int* ptr;

    // NULL
    int* nullPtr = NULL;

    // Array out-of-bounds access
    int arr[5];
    // Out of bounds access
    arr[10] = 42;

    // Function call without definition
    unusedFunction();

    // Uninitialized pointer
    *ptr = 5;

    // Null pointer dereference
    *nullPtr = 10;

    int errVar = 3

    return 0;
}
