int foo() {
  int x = 42;
  return x/0;
}

int main() {
  int y;

  y = 7;
  int x = foo();
  y = 10;

  return y + x;
}
