int main()
{
  #ifdef TIDYARGS
  int i = 1 / 0;
  #endif

  #ifdef SAARGS
  int* p = 0;
  *p = 42;
  #endif
}
