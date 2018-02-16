int main()
{
    int *p = 0;

    // codechecker_suppress [all] multi line
    // comments!

    sizeof(44);

    // codechecker_suppress [all] deliberate warning!

    sizeof(43);


    // No suppress comment.
    sizeof(42);

    // codechecker_suppress [all] deliberate segfault!
    return *p + 2;
}
