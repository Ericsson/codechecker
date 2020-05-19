// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

#include "path_end.h"

int g(int y){
    return div_zero(y);
}

int test(int z){
    if(z == 0){
        return g(z);
    }
}
