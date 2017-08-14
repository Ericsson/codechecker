int main()
{

#ifdef HAVE_NULL_DEREFERENCE
  int *ptr = nullptr;
#else
  int x = 0;
  int *ptr = &x;
#endif

  return *ptr;
}
