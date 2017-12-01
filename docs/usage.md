# CodeChecker HOWTO

This is lazy dog HOWTO to using CodeChecker analysis.
It invokes Clang Static Analyzer and Clang-Tidy tools to analyze your code.

Table of Contents
=================
* [Step 1: Integrate CodeChecker into your build system](#step-1)
* [Step 2: Analyze your code](#step-2)
  * [Cross-Compilation](#cross-compilation)
  * [Incremental Analysis](#incremental-analysis)
  * [Analysis Failures](#analysis-failures)
  * [Avoiding or Suppressing False Positives](#false-positives)
* [Step 3: Store analysis results in a CodeChecker DB and visualize results](#step-3)
* [Step 4: Fine tune Analysis configuration](#step-4)
  * [Ignore modules from your analysis](#ignore-modules)
  * [Enable/Disable Checkers](#enable-disable-checkers)
  * [Identify files that failed analysis](#identify-files)
* [Step 5: Integrate CodeChecker into your CI loop](#step-5)
  * [Storing & Updating runs](#storing-runs)
  * [ Alternative 1 (RECOMMENDED): Store the results of each commit in the same run](#storing-results)
    * [Jenkins Script](#storing-results-example)
  * [Alternative 2: Store each analysis in a new run](#storing-new-runs)
    * [Jenkins Script](#storing-new-runs-example)  
  * [Programmer checking new bugs in the code after local edit (and compare it to a central database)](#compare)

## <a name="step-1"></a> Step 1: Integrate CodeChecker into your build system
CodeChecker only analyzes what is also built by your build system.

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

## <a name="step-2"></a> Step 2: Analyze your code
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
 You can do the 1st and the 2nd step in one round by executing `check`
```
 cd tmux
 make clean
 CodeChecker check -b "make" -o ./reports
``` 
or to run on 22 threads

```
 CodeChecker check -j22 -b "make clean;make -j22" -o ./reports
```


### <a name="cross-compilation"></a> Cross-Compilation
Cross-compilers are auto-detected by CodeChecker, so 
the `--target` and the compiler pre-configured
include paths of `gcc/g++` are automatically passed to `clang` when analyzing.

**Make sure that the compilers used for building the project (e.g. `/usr/bin/gcc`) are
accessible when `CodeChecker analyze` or `check` is invoked.**

### <a name="incremental-analysis"></a> Incremental Analysis
 The analysis can be run for only the changed files and the `report-directory` will be
 correctly updated with the new results.
 
 ```
 cd tmux
 make clean
 CodeChecker check -b "make" -o reports
 
 #Change only 1 file in tmux
 vi ./cmd-find.c
 
 #Only cmd-find.c will be re-analyzed 
 CodeChecker check -b "make" -o reports
```
Now the `reports` directory contains also the results of the updated `cmd-find.c`.

### <a name="analysis-failures"></a> Analysis Failures

The `reports/failed` folder contains all build-actions that
were failed to analyze. For these there will be no results.

Generally speaking, if a project can be compiled with Clang then the analysis
should be successful always.  We support analysis for those projects which are
built only with GCC, but there are some limitations.

Possible reasons for failed analysis:
* The original GCC compiler options were not recognized by Clang.
* There are included headers for [GCC features which are
  not supported by Clang](/docs/gcc_incompatibilities.md).
* Clang was more strict when parsing the C/C++ code than the original compiler (GCC).
 Any non-standard compliant or GCC specific code needs to be removed to successfully analyze the file.
 One other solution may be to use the `__clang_analyzer__` macro. When the
 static analyzer is using clang to parse source files, it implicitly defines
 the preprocessor macro
 [__clang_analyzer__](https://clang-analyzer.llvm.org/faq.html#exclude_code). One can use this macro to
 selectively exclude code the analyzer examines.
* Clang crashed during the analysis.

### <a name="false-positives"></a> Avoiding or Suppressing False positives
Sometimes the analyzer reports correct code as incorrect. These findings are called false positives.
Having a false positive indicates that the analyzer does not understand some properties of the code.

CodeChecker provides two ways to get rid off false positives.

1. The first and the preferred way is to make your code understood by the analyzer. 
E.g. by adding `assert`s to your code, analyze in `debug` build mode and annotate your function parameters. 
For details please read the [False Positives Guide](false_positives.md).

2. If step 1) does not help, use CodeChecker provided [in-code-suppression](user_guide.md#suppression-code)
to mark false positives in the source code. This way the suppression information is kept close to the suspicious 
line of code. Although it is possible, it is not recommended to suppress false positives
on the Web UI only, because this way the suppression will be stored in a database that is unrelated to the source code.

## <a name="step-3"></a> Step 3: Store analysis results in a CodeChecker DB and visualize results
You can store the analysis results in a central database and view the results in a web viewer
1. Start the CodeChecker server locally on port 8555 (using SQLite DB, which is not recommended for multi-user central deployment)
create a workspace directory, where the database will be stored.
```
 mkdir ./ws
 CodeChecker server -w ./ws -v 8555
```
A default product called `Default` will be automatically created where you can store your results.

2. Store the results in the server under run name "tmux" (in the `Default` product):
```
 CodeChecker store ./reports --name tmux --url http://localhost:8555/Default 
```

The URL is in `PRODUCT_URL` format:
`[http[s]://]host:port/ProductEndpoint`
Please note that if you start the server in secure mode (with SSL) you will need to use the `https` protocol prefix.
The default protocol is `http`.
See [user guide](/docs/user_guide.md#product_url-format) for detailed description of the `PRODUCT_URL` format.

3. View the results in your web browser
 http://localhost:8555/Default

## <a name="step-4"></a> Step 4: Fine tune Analysis configuration
### <a name="ignore-modules"></a> Ignore modules from your analysis 

You can ignore analysis results for certain files for example 3rd party modules.
For that use the `-i` parameter of the analyze command:
```
 -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                        Path to the Skipfile dictating which project files
                        should be omitted from analysis. Please consult the
                        User guide on how a Skipfile should be laid out.
```
For the skip file format see the [user guide](/docs/user_guide.md#skip-file).

```
 CodeChecker analyze -b "make" -i ./skip.file" -o ./reports
```

### <a name="enable-disable-checkers"></a> Enable/Disable Checkers

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

### <a name="identify-files"></a> Identify files that failed analysis
After execution of
```
 CodeChecker analyze build.json -o reports
```
the failed analysis output is collected into 
 `./reports/failed`
directory.

This means that analysis of these files failed and there is no Clang Static Analyzer output for these compilation commands.


## <a name="step-5"></a> Step 5: Integrate CodeChecker into your CI loop

This section describes a recommended way on how CodeChecker is designed to be
used in a CI environment to

* Generate daily report summaries
* Implement CI guard to prevent the introduction of new bugs into the codebase

In CodeChecker each bug has a unique hash identifier that is independent of
the exact line number therefore resistant to shifts in the source code. With
this feature CodeChecker can recognize the same and new bugs in two different
version of the same source file.

**In summary:**
* Create a single run for each module in each branch and keep it up to date
  with code changes (commits). The CI loop then can compare pull requests
  (commit attempts) against this run and list *new* bugs in the changed code.
  Programmers can also compare their local edits to this run to see if they
  would introduce any new issues.
* Store daily runs of a module every day in a new run post-fixed with date.
* You can query *new* and *resolved* bugs using the
  [`cmd diff`](user_guide.md#show-differences-between-two-runs-diff) or the
  Web GUI.
* Programmers should use [in-code-suppression](user_guide.md#suppression-code) 
  to tell the CI guard that a report is false positive and should be ignored.
  This way your suppressions remain also resistant to eventual changes of the
  bug hash (generated by clang).
 
### <a name="storing-runs"></a> Storing & Updating runs
Let us assume that you want to analyze your code-base daily and would like to
send out an email summary about any newly introduced and resolved issues.

You have two alternatives:
1. Store the results of each commit in the same run (performance efficient way) 
2. Store each analysis in a new run

#### <a name="storing-results"></a> Alternative 1 (RECOMMENDED): Store the results of each commit in the same run 

Let us assume that at each commit you would like to keep your analysis 
results up-to-date and send an alert email to the programmer if a new bug is
introduced in a "pull request", and if there is a new bug in the
to-be-committed code, reject this "pull request".

A single run should be used to store the analysis results of module on a
specific branch: `<module_name>_<branch>`.

The run should be always updated when a new commit is merged to reflect the
analysis status of the latest code version on your branch.

Let's assume that user `john_doe` changed `tmux/attributes.c` in tmux. The CI
loop reanalyzes `tmux` project and sends an email with reject if new bug was
found compared to the master version, or accepts and merges the commit if no
new bugs were found.

Let's assume that the working directory is `tmux` under the CI job's
_workspace_, that has the source code with John Doe's modifications checked
out.

1. Generate a new log file for the new code
```
 CodeChecker log -b "make" -o compilation.json
```
2. Re-analyze the changed code of John Doe. If your "master" CI job
```
 CodeChecker analyze compilation.json -o ./reports-PR
```
3. Check for new bugs in the run
```
 CodeChecker cmd diff -b tmux_master -n ./reports-PR --new --url http://localhost:8555/Default
```

If new bugs were found, reject the commit and send an email with the new bugs to John.

If no new bugs were found:

4. Merge the changes into the master branch
	
5. Update the analysis results according to the new code version:
```
 CodeChecker store ./reports-john-doe --url http://localhost:8555/Default --name tmux_master
```

If John finds a false positive report in his code and so the CI loop would
prevent the merge of his pull request, he can suppress the false positive by
amending the following suppression comment in his code a line above the bug or
add `assertions` or `annotations` so that the false positive reports are avoided (see [False Positives Guide](false_positives.md)). 

An example, as follows:

~~~{.cpp}
int x = 1;
int y;

if (x)
  y = 0;

// codechecker_suppress [core.NullDereference] suppress all checker results
int z = x / y; // warn
~~~

See [User guide](user_guide.md#suppression-in-the-source-code) for more
information on the exact syntax.

##### <a name="storing-results-example"></a> Jenkins Script

Please find a [Shell Script](script_update.md) that can be used 
in a Jenkins or any other CI engine to report new bugs. 

#### <a name="storing-new-runs"></a>Alternative 2: Store each analysis in a new run

Each daily analysis should be stored as a new run name, for example using the
following naming convention: `<module_name>_<branch_name>_<date>`.

Using `tmux` with daily analysis as example:

1. Generate a new log file
```
 CodeChecker log -b "make" -o compilation.json
```
2. Re-analyze the project. Make sure you use the same analyzer options all the
   time, as changing enabled checkers or fine-tuning the analyzers *may*
   result in new bugs being found.
```
 CodeChecker analyze compilation.json -o ./reports-daily
```
3. Store the analysis results into the central CodeChecher server
```
 CodeChecker store ./reports --url http://localhost:8555/Default --name tmux_master_$(date +"%Y_%m_%d")
```

This job can run daily and will store the results in different runs
identified with the date.

Then you can query newly introduced bugs in the following way.
```
 CodeChecker cmd diff -b tmux_master_2017_08_28 -n tmux_master_2017_08_29 --new --url http://localhost:8555/Default
```

If you would like to generate a report page out of this using a script, you can get the results in `json` format too:
```
 CodeChecker cmd diff -b tmux_master_2017_08_28 -n tmux_master_2017_08_29 --new --url http://localhost:8555/Default -o json
```

> **Note:** Don't forget to delete old runs you don't need to save database
> space.

##### <a name="storing-new-runs-example"></a> Jenkins Script

Please find a [Shell Script](script_daily.md) that can be used 
in a Jenkins or any other CI engine to report new bugs. 


### <a name="compare"></a> Programmer checking new bugs in the code after local edit (and compare it to a central database)
Say that you made some local changes in your code (tmux in our example) and
you wonder whether you introduced any new bugs. Each bug has a unique hash
identifier that is independent of the line number, therefore resistant to
shifts in the source code. This way, newly introduced bugs can be detected
compared to a central CodeChecker report database.

Let's assume that you are working on the master branch and the analysis of the
master branch is already stored under run name `tmux_master`.

1. You make **local** changes to tmux
2. Generate a new log file
```
 CodeChecker log -b "make" -o compilation.json
```
3. Re-analyze your code. You are well advised to use the same `analyze`
   options as you did in the "master" CI job: the same checkers enabled, the
   same analyzer options, etc.
```
 CodeChecker analyze compilation.json -o ./reports
```
4. Compare your local analysis to the central one
```
 CodeChecker cmd diff -b tmux_master -n ./reports --new --url http://localhost:8555/Default
```
