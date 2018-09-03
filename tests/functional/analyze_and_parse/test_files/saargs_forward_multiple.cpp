int main()
{

#if defined(HAVE_NULL_DEREFERENCE1) && defined(HAVE_NULL_DEREFERENCE2)
  int *ptr = nullptr;
#else
  int x = 0;
  int *ptr = &x;
#endif

  return *ptr;
}
