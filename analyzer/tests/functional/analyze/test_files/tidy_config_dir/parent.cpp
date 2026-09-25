int parent_sizeof() {
    return static_cast<int>(sizeof(sizeof(int)));
}

int parent_unused(int used, int unused) {
    return used;
}

int parent_braces(int x) {
    if (x) return 1;
    return 0;
}
