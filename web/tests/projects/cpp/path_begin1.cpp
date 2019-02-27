// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

#include "path_end.h"

int f(int x){
    if(x == 0){
        x = div_zero(x);
        return x;
    }
}
