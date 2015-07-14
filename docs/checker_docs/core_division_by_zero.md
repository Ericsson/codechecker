DivisionByZero
================

Description
-------------

This checker finds bugs when division by zero happens.

Example
-------------

~~~~~~{.cpp}
int doubleOrNull(int a)
{
    return a > 0 ? 2*a : 0;
}

void f()
{
    int a = 0.0;
    int b = doubleOrNull(a);
    a = a / b;  // Division by zero
}
~~~~~~

Configuration
-------------
None

Limitations
-------------
None

Solution
-------------
Check the divisor for zero.
For example, here is the fix for the previous code.
if (b != 0) a = a / b;
