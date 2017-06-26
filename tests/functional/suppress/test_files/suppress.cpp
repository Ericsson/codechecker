int main()
{
    int *p = 0;

    // codechecker_suppress [all] deliberate segfault!
    return *p + 2;
}
