# CodeChecker HOWTO

This is lazy dog HOWTO to using CodeChecker analysis.
It invokes Clang Static Analyzer and Clang-Tidy tools to analyze your code.

## Step1: Inegrate CodeChecker into your build system
Codechecker only analyzes what is also built by your build system. 

1. Select a module to build (open source tmux in this example).
```
cd tmux
./configure
```
2. Clean that module. e.g. `make clean`
```
 make clean
```
3. Log your build:
``` 
CodeChecker log -b "make" -o compilation.json
```
4. Check the contents of compilation.json. If everything goes well it should contain the `gcc` calls.
```
cat ./compilation.json
```

**What to do if the `compilation.json` is empty?**
* Make sure that your build system actually invoked the compiler (e.g. `gcc`,`g++`). 
  In case your software was built once (and the binaries are already generated),
  the compiler will not be invoked. In this case do a build cleanup (e.g. `make clean`) and 
  retry to log your build.
  
* Make sure that the `CC_LOGGER_GCC_LIKE` environment variable is set correctly and contains your compilers. 
  For detailed description see the [user guide](/docs/user_guide.md#1-log-mode).

* MacOS users need `intercept-build` to be available on the system, 
  and in most cases, _System Integrity Protection_ needs to be turned off. 
  See the [README](/README.md#mac-os-x) for details.

## Step2: Analyze your code 
Once the build is logged successfully (and the `compilation.json`) was created, you can analyze your project.

1. Run the analysis: 
```
 CodeChecker analyze compilation.json -o ./reports
```
2. View the analysis results in the command line
```
 CodeChecker parse ./reports
```
Hint:
 You can do the 1st and the 2nd step in one round by execution quickcheck
 ```
 cd tmux
 make clean
 CodeChecker quickcheck -b "make"
or to run on 22 thread
 CodeChecker quickcheck -j22 -b "make clean;make -j22"
```

[What to do if the analysis fails (analysis settings for cross-compilation)](/docs/cross-compilation.md)

## Step3: Store analysis results in a CodeChecker DB and visualize results 
You can store the analysis results in a central database and view the results in a web viewer
1. Start the CodeChecker server locally on port 8555 (using sqlite db, which is not recommended for multi-user central deployment)
create a workspace directory, where the database will be stored.
```
 mkdir ./ws
 CodeChecker server -w ./ws -v 8555
```
2. Store the results in the server under run name "tmux":
```
 CodeChecker store ./reports --host localhost --port 8555 --name tmux
```
3. View the results in your web browser
 http://localhost:8555

## Step4: Fine tune Analysis configuration
### Ignore modules from your analysis 

You can ignore analysis results for certain files for example 3rd party modules.
For that use the `-i` parameter of the analyze command:
```
 -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                        Path to the Skipfile dictating which project files
                        should be omitted from analysis. Please consult the
                        User guide on how a Skipfile should be laid out.
```
For the skip file format see the [user guide](/docs/user_guide.md#skip-file ).

```
 CodeChecker analyze -b "make" -i ./skip.file" -o ./reports
```

### Enable/Disable Checkers

You can list the checkers using the following command
```
 CodeChecker checkers --details
```
those marked with (+) are enabled by default.

You may want to enable more checkers or disable some of them using the -e, -d switches of the analyze command.

For example to enable alpha checkers additionally to the defaults
```
 CodeChecker analyze -e alpha  -b "make" -i ./skip.file" -o ./reports
```

### Identify files that were failed to analyze
After execution of
```
 CodeChecker analyze build.json -o reports
```
the failed analysis output is collected into 
 `./reports/failed`
directory.

This means that analysis of these files failed and there is no Clang Static Analyzer output for these compilation commands.

### Showing new bugs in your code after local edit
Say that you made some local changes in your code (tmux in our example) and you wonder whether you introduced any new bugs.

Let's assume that you already stored the tmux analysis results in a CodeChecker server running on `localhost:8555` under run name `tmux` 
See Step3: `CodeChecker store ./reports --host localhost --port 8555 --name tmux`

1. You make local changes to to tmux
2. Generate a new log file
```
 CodeChecker log -b "make" -o compilation.json
```
3. Re-analyze your code
```
 CodeChecker analyze compilation.json ./reports
```
4. Compare your local analysis to the central one
```
 CodeChecker cmd diff -b tmux -n ./reports --new --host localhost --port 8555
```
