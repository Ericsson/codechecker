
// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------


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

