#include <stdlib.h>
  
static int *table = NULL;
static size_t size = 0;
 
int insert_in_table(size_t pos, int value) {
  if (size < pos) {
    int *tmp;
    size = pos + 1;
    tmp = (int *)realloc(table, sizeof(*table) * size);
    if (tmp == NULL) {
      return -1;   /* Failure */
    }
    table = tmp;
  }

	// Store to null pointer of type 'int'.
  table[pos] = value;
  return 0;
}

int main(void)
{
	insert_in_table(0, 42);
}