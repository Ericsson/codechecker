#include <cstring>

// Triggers 'bugprone-sizeof-expression' (a member of the group which the
// parent directory enables with the 'bugprone-*' glob).
int glob_sizeof() {
    return static_cast<int>(sizeof(sizeof(int)));
}

// Triggers 'bugprone-suspicious-string-compare', another member of the same
// group, which no directory disables.
bool glob_string_compare(const char *a, const char *b) {
    return strcmp(a, b) == -1;
}

// Triggers 'readability-braces-around-statements' and
// 'readability-magic-numbers', members of a group which only the
// 'group_widened' directory enables.
int glob_braces(int x) {
    if (x) return 42;
    return 0;
}
