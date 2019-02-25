// -----------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -----------------------------------------------------------------------------

#include "path_end.h"

int g(int y){
    return div_zero(y);
}

int test(int z){
    if(z == 0){
        return g(z);
    }
}
