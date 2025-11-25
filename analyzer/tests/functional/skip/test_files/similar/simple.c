// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// This file is to be included in a --file argument.

void main(int z) {
  int x;
  if (z == 0)
    x = 1 / z; // warn
}
