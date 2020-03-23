function foo() {
  var x = 10;

  if (x = 1 ||
      x = 2) return 0;

  return x;
}
