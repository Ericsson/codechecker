#include <cstdlib>
void g(void *i) {
  i = malloc(sizeof(int));
  free(i);
  free(i);
}
