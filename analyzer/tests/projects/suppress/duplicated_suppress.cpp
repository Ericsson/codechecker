int duplicatedSuppress();

int duplicatedSuppress()
{
    // codechecker_suppress [bugprone-sizeof-expression] Same suppress comment twice.
    // codechecker_suppress [core.DivideZero] Unmatching suppress comment.
    // codechecker_suppress [bugprone-sizeof-expression] Same suppress comment twice.
    return sizeof(42);
}
