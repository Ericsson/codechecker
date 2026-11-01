// COMPILE: clang -g -fsanitize=address -fomit-frame-pointer asan3.c
int main(int argc, char **argv) {
  int stack_array[100];
  stack_array[1] = 0;
  return stack_array[argc + 100];  // BOOM
}
