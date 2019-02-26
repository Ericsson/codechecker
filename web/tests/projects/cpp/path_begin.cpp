
// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------


int div_zero2(int z, int w) {

  if (z == 0){
    int x = 1 / z; // warn
    return x;
  }

  if (w==0){
    z=0;
    int x = 1 / z; // warn
    return x;
  }

}

int f(int x){
    return div_zero2(0, x);
}

int g(int x){
    return div_zero2(x, 0);
}

