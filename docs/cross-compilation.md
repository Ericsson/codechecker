# How to analyze a project that contains cross-compilation 

It may happen that due to special gcc build-time configuration (see https://gcc.gnu.org/onlinedocs/libstdc++/manual/configure.html) 
clang used by CodeChecker cannot do the analysis due different configuration.
This is especially the case when gcc is used for **cross-compilation**.

**In case of cross-compilation always use the same target for clang analysis as you use in the gcc build.** 

The list of targets supported by clang is described
[here](http://llvm.org/doxygen/Triple_8h_source.html). 

A file (`commonhandler.cpp`) for example compiles like this to powerpc target:
``` 
powerpc64-linux-g++ -c -o /home/<username>/mylib_ppc64_linux/commonhandler.cpp
```
when we try to analyze this file with Clang Static Analyzer with the same command line options like
``` 
 CodeChecker check -b "powerpc64-linux-g++ -c -o /home/<username>/mylib_ppc64_linux/commonhandler.cpp" --analyzers clangsa --verbose debug
```
we get the following error:
```
 .../platform_ifc/RTLIB.h:42: 
 /proj/.../inc/myprod_te_lib.h:60:10: fatal error: 'lib.h' file not found
 #include <lib.h>                 /* Original lib.h           */        
 1 error generated.
```
Why? Because `powerpc64-linux-g++` is an product specific cross compiler and has some compiled in include paths, and defines, while clang, 
that was used by CodeChecker is configured to compile to x86_64 Linux target.

**Solution**
You can pass any parameters to clang using `--saargs` parameter.

For example the error above can be solved for Clang Static Analyzer analysis like

```
 CodeChecker check -b "powerpc64-linux-g++ -c -o
 /home/<username>/mylib_ppc64_linux/commonhandler.cpp" --analyzers clangsa --saargs ./saargs.txt
```

where
```
 saargs.txt:
 
 -target ppc64 
 -I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include/c++/5.2.0 
 -I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include/c++/5.2.0/powerpc64-wrs-linux 
 -I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include/c++/5.2.0/backward 
 -I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include
```
similarly create the same configuration for clang-tidy (with a littlebit different syntax):
```
tidyargs.txt:

 -extra-arg="-target" -extra-arg="ppc64" 
 -extra-arg="-I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include/c++/5.2.0" 
 -extra-arg="-I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include/c++/5.2.0/powerpc64-wrs-linux" 
 -extra-arg="-I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include/c++/5.2.0/backward" 
 -extra-arg="-I/proj/platform/linux/sdk_install/sysroots/ppc64-linux/usr/include"
```

So the full analysis command will be
```
 CodeChecker check -b "powerpc64-linux-g++ -c -o
 /home/<username>/mylib_ppc64_linux/commonhandler.cpp" --saargs ./saargs.txt --tidyargs ./tidyargs.txt
```

We needed to add the powerpc64 compilation target (`-target ppc64`) and the standard c++ library paths for 5.2.0 (which is configured into the the powerpc64-linux-g++ binary.
