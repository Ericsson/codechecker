int child_sizeof() {
    return static_cast<int>(sizeof(sizeof(int)));
}

int child_unused(int used, int unused) {
    return used;
}

int child_braces(int x) {
    if (x) return 1;
    return 0;
}
