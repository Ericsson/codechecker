// COMPILE: clang++ -g -fsanitize=address -fomit-frame-pointer asan2.cpp
int main(int argc, char **argv) {
  int *array = new int[100];
  array[0] = 0;
  int res = array[argc + 100];  // BOOM
  delete [] array;
  return res;
}
