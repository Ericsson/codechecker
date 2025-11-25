int* f() {
  // We only enabled clang-diagnostic-return-stack-address checker,
  // so there should be no finding for division by zero.
  int a = 5/0;

  // The line below should raise clang-diagnostic-return-stack-address error
  return &a;
}

int main (void) {
  return *f();
}
