#define MY_NULL 0

class C
{
public:
  C() {}

private:
  int a;
};

int main()
{
  int* p1 = 0;
  int* p2 = MY_NULL;
  C c;
  return 0;
}
