void *operator new(unsigned long k) {
  (void)(10/k);
  return nullptr;
}
