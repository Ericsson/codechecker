void *operator new(unsigned long);

void foo() {
  void *ptr = ::operator new(0ul);
  (void)ptr;
}
