// COMPILE: clang -g -fsanitize=address -fomit-frame-pointer asan4.c
int global_array[100] = {-1};
int main(int argc, char **argv) {
  return global_array[argc + 100];  // BOOM
}
