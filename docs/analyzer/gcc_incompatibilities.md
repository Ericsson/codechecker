# GCC - Clang system headers incompatibilities

Table of Contents
=================

* [GCC - Clang system headers incompatibilities](#gcc---clang-system-headers-incompatibilities)
* [Table of Contents](#table-of-contents)
   * [GCC fixincludes](#gcc-fixincludes)
   * [System headers for Intel vector instructions](#system-headers-for-intel-vector-instructions)
   * [Other system headers in GCC](#other-system-headers-in-gcc)
      * [backtrace.h, backtrace-supported.h](#backtraceh-backtrace-supportedh)
      * [cross-stdarg.h](#cross-stdargh)
      * [omp.h](#omph)
      * [openacc.h](#openacch)
      * [quadmath.h, quadmath_weak.h](#quadmathh-quadmath_weakh)
      * [sgxintrin.h](#sgxintrinh)
      * [stdfix.h](#stdfixh)
      * [stdint-gcc.h](#stdint-gcch)

## GCC fixincludes

A little-known part of GCC's build process is a script called "fixincludes", or
`fixinc.sh`. Purportedly, the purpose of this script is to fix "non-ANSI system
header files" which GCC "cannot compile" (https://ewontfix.com/12/).
Some examples of these fixes are:

* Changing AIX's _LARGE_FILES redirection of open to open64, etc. to use GCC's
  `__asm__` keyword rather than #define, as the latter breaks C++.
* Exposing the long double math functions in math.h on Mac OS 10.3.9, which
  inexplicably omitted declarations for them.
* Adding workaround for Linux 2.2 and earlier kernel bug with direction flag to
  FD_ZERO macros.

The fixincludes process iterates over each header file it finds under
`/usr/include` (or whatever the configured include directory is), applies a set
of heuristics based on the filename, machine tuple, and a regular expression
matched against the file contents, and if these rules match, it applies a
sequence of sed commands to the file. As of this writing, there are 228 such
"hacks" that may be applied. The output is then stored in GCC's private
include-fixed directory (roughly `/usr/lib/gcc/$MACH/$VER/include-fixed`), which
GCC searches before the system include directory, thus "replacing" the original
header when the new GCC is used.

Fixincludes is a bad idea and a bad hack, the [Gentoo Linux distribution simply
removes the whole generated directory](https://sources.gentoo.org/cgi-bin/viewvc.cgi/gentoo-x86/eclass/toolchain.eclass?view=markup&sortby=log#l1524).
Consequently, Clang (from version 3.8) skips the `include-fixed` include path
even if it is built with GCC and configured to use GCC's libstdc++
(https://bugs.launchpad.net/ubuntu/+source/llvm-toolchain-3.8/+bug/1573778).

The practical difficulty in CodeChecker is that we're appending the implicit
include paths of the compiler which is used during the comiplation of the
analyzed project in the logging phase. The reason of this is that we'd like to
see the same build environment during the analysis. However, Clang also has its
own implicit include paths. These are almost the same of GCC's paths except for
`include-fixed` directories because these are GCC specific. Unfortunately some
projects require the additiion of these paths but some do not. So
`--keep-gcc-include-fixed` flag can control whether we should keep these during
the analysis. There is another unanswered question: currently the GCC implicit
include paths are added with `-isystem` flag. This appends the paths _before_
the analyzer Clang's implicit paths. However, we could also use
`-isystem-after` which appends them _after_ Clang's paths. According to our
experiences `-isystem` has to be used otherwise we get compilation error during
the analysis.

References:

* [https://www.gnu.org/software/autogen/fixinc.html](https://www.gnu.org/software/autogen/fixinc.html)
* [https://android.googlesource.com/toolchain/gcc/+/master/gcc-4.8.3/fixincludes/README](https://android.googlesource.com/toolchain/gcc/+/master/gcc-4.8.3/fixincludes/README)
* [https://ewontfix.com/12/](https://ewontfix.com/12/)

## System headers for Intel vector instructions

GCC and Clang support native vector operations differently.  The corresponding
Intel intrinsics (for MMX, SSE, AVX, etc) have their own headers in a compiler
specific include directory.  For instance, the `_mm_add_ss` for SSE can be
found in xmmintrin.h.  GCC implements the intrinsic by delegating to it's own
builtin intrinsic:
```c
__m128 _mm_add_ss (__m128 __A, __m128 __B)
{
  return (__m128) __builtin_ia32_addss ((__v4sf)__A, (__v4sf)__B);
}
```
Meanwhile Clang handles vector types commonly, therefore there is no such
compiler intrinsic as `__builtin_ia32_addss` in Clang. Clang uses the common
operators on the vector types to implement `_mm_add_ss`:
```c
__m128 _mm_add_ss(__m128 __a, __m128 __b)
{
  __a[0] += __b[0];
  return __a;
}
```
Because of this implementation difference Clang simply skips the system header
path for GCC intrinsics even if Clang is built with GCC and configured to use
GCC's libstdc++.
For example:
```bash
$ clang -E -x c -v -
...
#include <...> search starts here:
 /usr/local/include
 /usr/lib/llvm-4.0/bin/../lib/clang/4.0.0/include
 /usr/include/x86_64-linux-gnu
 /usr/include

$ gcc -E -x c -v -
#include <...> search starts here:
 /usr/lib/gcc/x86_64-linux-gnu/7/include
 /usr/local/include
 /usr/lib/gcc/x86_64-linux-gnu/7/include-fixed
 /usr/include/x86_64-linux-gnu
 /usr/include

```

By default the include paths which contain at least one header with `intrin.h`
postfix are excluded from among the collected paths. If for some reason these
are needed for the analysis these can be kept with `--keep-gcc-intrin` flag
after `CodeChecker analyze` and `CodeChecker check` commands.

References:

* [https://software.intel.com/sites/landingpage/IntrinsicsGuide/](https://software.intel.com/sites/landingpage/IntrinsicsGuide/)
* [http://clang.llvm.org/compatibility.html#vector_builtins](http://clang.llvm.org/compatibility.html#vector_builtins)
* [http://clang.llvm.org/docs/LanguageExtensions.html#vectors-and-extended-vectors](http://clang.llvm.org/docs/LanguageExtensions.html#vectors-and-extended-vectors)

## Other system headers in GCC
GCC implements many other features which are not implemented in Clang.  These
headers are in the same directory where the Intel vector intrinsic headers are.
E.g. in:
```
/usr/lib/gcc/x86_64-linux-gnu/7/include
```
Some of these headers may be used with Clang, but the users must be aware that
by adding GCC's internal header path to the include search path would result
compilation error if vector instructions are used as well.

#### `backtrace.h`, `backtrace-supported.h`

 Part of libbacktrace. It uses the GCC unwind interface to collect a stack
 trace, and parses DWARF debug info to get file/line/function information.  The
 library may be linked into a program or library and used to produce symbolic
 backtraces.  Sample uses would be to print a detailed backtrace when an error
 occurs or to gather detailed profiling information.
 We can use the library with Clang by adding gcc's intrinsic system include,
 for instance:
 ```
 clang -lbactrace -I
 /usr/lib/gcc/x86_64-pc-linux-gnu/6.2.1/include bt.c
 ```
 However, using the library this way together with vector
 instructions (e.g. from xmmintrin.h) would fail the compilation and the
 analysis.

#### `cross-stdarg.h`

 Contains macros to handle functions with variadic arguments (vararg, `va_list`,
 `va_start`, etc) during cross platform compilation for non x64 platforms. It
 defines ms_abi and sysv_abi specific macros like `__builtin_ms_va_list`.
 There is no need to use this header directly, rather function attributes
 should be used as described in both compilers' documentation:

 * [https://gcc.gnu.org/onlinedocs/gcc/x86-Function-Attributes.html](https://gcc.gnu.org/onlinedocs/gcc/x86-Function-Attributes.html)
 * [https://clang.llvm.org/docs/AttributeReference.html#ms-abi-gnu-ms-abi](https://clang.llvm.org/docs/AttributeReference.html#ms-abi-gnu-ms-abi)

#### `omp.h`

 Part of libgomp. As of today within mainline GCC, the libgomp library, which up
 to now has been known as the GNU OpenMP Runtime Library, has been renamed to
 GNU Offloading and Multi Processing Runtime Library.
 The libgomp library has grown beyond just OpenMP to now being utilized for
 OpenMP 4 offloading capabilities, OpenACC support, AMD HSA support, etc.

 According to one [stackoverflow
 post](https://stackoverflow.com/questions/33357029/using-openmp-with-clang) it
 may work with Clang.
 We can use the library with Clang by adding gcc's intrinsic system include,
 for instance:
 ```
 clang++ -I/usr/lib/gcc/x86_64-linux-gnu/4.9/include
 -fopenmp=libiomp5 -o test test.cpp
 ```
 However, using the library this way together with vector
 instructions (e.g. from xmmintrin.h) would fail the compilation and the
 analysis.

#### `openacc.h`

 Part of libgomp. OpenACC (for open accelerators) is a programming standard for
 parallel computing developed by Cray, CAPS, Nvidia and PGI. The standard is
 designed to simplify parallel programming of heterogeneous CPU/GPU systems.

#### `quadmath.h,` `quadmath_weak.h`

 Part of  the GCC Quad-Precision Math Library Application Programming Interface
 (API).
 All math functions in this lib (acosq, asinq) uses the type `__float128`.
 We can use the library with Clang by adding gcc's intrinsic system include,
 for instance:
 ```
 clang -O0 -m32 -lquadmath -I
 /usr/lib/gcc/x86_64-pc-linux-gnu/6.2.1/include float128.c
 ```
 However, using the library this way together with vector
 instructions (e.g. from xmmintrin.h) would fail the compilation and the
 analysis.

 Related: [Problem about 128bit floating-point operations in x86
 machines](http://lists.llvm.org/pipermail/llvm-dev/2016-December/108033.html)

#### `sgxintrin.h`

 Support for Intel SGX extension. Contains inline assembly macros.
 This Intel technology is for application developers who are seeking to protect
 select code and data from disclosure or modification. Intel® SGX makes such
 protections possible through the use of enclaves, which are protected areas of
 execution in memory.

 We can use the library with Clang by adding gcc's intrinsic system include.
 However, using the library this way together with vector
 instructions (e.g. from xmmintrin.h) would fail the compilation and the
 analysis.

#### `stdfix.h`

 Fixed-Point Arithmetic Support. Digital Signal Processors have traditionally
 supported fixed-point arithmetic in hardware. But more recently, many
 DSP-enhanced RISC processors are starting to support fixed-point data types as
 part of their native instruction set. When the precision requirements of the
 application can be met with fixed-point arithmetic, then this is preferred
 since it can be smaller and more efficient than floating-point hardware. DSP
 algorithms often represent the data samples and the coefficients used in the
 computation as fractional numbers (between -1 and +1) to avoid magnitude
 growth of a multiplication product. Fractional data type, where there are zero
 integer bits, is a subset of the more general fixed-point data type.

 The types `_Fract`, `_Accum`, `_Sat` are not supported by Clang.
 Related: https://groups.google.com/forum/#!topic/llvm-dev/G7MDIj4Pq6w

#### `stdint-gcc.h`

 Fixed size integers (e.g `uint64_t`). Use `<stdint.h>` instead of this header.
