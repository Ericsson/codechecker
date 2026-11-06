int narrow_sizeof() {
    return static_cast<int>(sizeof(sizeof(int)));
}

int narrow_unused(int used, int unused) {
    return used;
}
