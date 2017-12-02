int clang_analyzer_crash(int * i);
int foo(int);

void test()
{
    int * ptr = 0;
    foo(3); // This CallExpr will trigger the load of lib.c's AST
    clang_analyzer_crash(ptr); // The analyzer will crash at this CallExpr
}

