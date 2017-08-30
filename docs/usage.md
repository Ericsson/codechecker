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


## Step5: Integrate CodeChecker into your CI loop

This section describes a recommended "way of working" about how CodeChecker is designed to be used
in a CI environment to
* generate daily report summaries
* implement CI guard to prevent the introduction of new bugs into the code-base.

In CodeChecker each bug has a unique hash identifier that is independent of the exact line number 
therefore resistant to shifts in the source code.
With this feature CodeChecker can recognize the same and new bugs in two different version of the same source file.

**In summary:**
* Store daily runs of a module every day in a new run post-fixed with date. You can query  *new* and *resolved* bugs
 using the [`cmd diff`](docs/user_guide.md#show-differences-between-two-runs-diff) or the WEB GUI.
* Create a single run for each module in each branch and keep it up to date with code changes (commits). The CI
 loop then can compare pull requests (commit attempts) against this run and list *new* bugs in the changed code. 
 Programmers can also compare their local edits to this run to see if they would introduce any new issues.
* Programmers should use [in-code-suppression](docs/user_guide.md#suppression-in-the-source-code) 
  to tell the CI guard that a report is false positive and should be ignored. This way your suppressions remain
  also resistant to eventual changes of the bug hash (generated by clang). 
 
### Storing daily runs
Let us assume that you want to analyze your code-base daily and would like to send out an 
email summary about any newly introduced and resolved issues.

**Store each analysis into a new run.**
Each daily analysis should be stored as a new run name with for example the following naming convention:
`<module_name>_<branch_name>_<date>`

For example to analyze `tmux` project daily.
1. Generate a new log file
```
 CodeChecker log -b "make" -o compilation.json
```
2. Re-analyze the code
```
 CodeChecker analyze compilation.json ./reports-daily
```
3. Store the analysis results into the central database.
```
 CodeChecker store ./reports --host codechecker.central --port 8555 --name tmux_master_2017_08_28
```

and the next day repeat **Step 1** to **Step 4** and store the results under run name `tmux_master_2017_08_29`.

Then you can query newly introduced bugs in the following way.
```
 CodeChecker cmd diff -b tmux_master_2017_08_28 -n tmux_master_2017_08_29  --new --host codechecker.central --port 8555
```
If you would like to generate a report page out of this using a script, you can get the results in `json` format too:
```
 CodeChecker cmd diff -b tmux_master_2017_08_28 -n tmux_master_2017_08_29  --new --host codechecker.central --port 8555 -o json
```

*Note:* Don't forget to delete old runs you don't need to save database space.

### Storing the results of each commit and guarding the introduction of new bugs
Let us assume that at each commit you would like to keep your analysis 
results up-to-date and send an alert email to the programmer if a new
bug is to be introduced in a "pull request". 
Also when there is a new bug in the uploaded code, reject the "pull request".

A single run should be used to store the analysis results of module on a specific branch: 
`<module_name>_<branch>`

The run should be always updated when a new commit is merged 
to reflect the analysis status of the latest code version on your branch.

Let's assume that user `john_doe` changed `tmux/attributes.c` in tmux. 
The CI loop re-analizes tmux project and sends an email with reject if new bug was found compared to the master version, or
accepts and merges the commit if no new bugs were found. 

Let's assume that the working directory is `tmux` containing John Doe's modifications. 

1. Generate a new log file for the new code
```
 CodeChecker log -b "make" -o compilation.json
```
2. Re-analyze the changed code of john_doe
```
 CodeChecker analyze compilation.json ./reports-john-doe
```
3. Check for new bugs in the run
```
 CodeChecker cmd diff -b tmux_master -n ./reports-john-doe --new --host codechecker.central --port 8555
```

If new bugs were found, reject the commit and send an email with the new bugs to John.

If no new bugs were found:

4. Merge the changes into the master branch
	
5. Update the analysis results according to the new code version:
```
 CodeChecker store ./reports-john-doe --host codechecker.central --port 8555 --name tmux_master
```

If John finds a false positive report in his code and so the CI loop would prevent the merge of his pull request,
he can suppress the false positive by amending the following suppression commend in his code a line above the bug
```
// codechecker_suppress [core.NullDereference] suppress all checker results
  x = 1; // warn
```
See [User guide](docs/user_guide.md#suppression-in-the-source-code) for more information.


### Programmer checking new bugs in the code after local edit (and compare it to a central database)
Say that you made some local changes in your code (tmux in our example) and you wonder whether you introduced any new bugs.
Each bug has a unique hash identifier that is independent of the line number, therefore resistant to shifts in the source code.
This way, newly introduced bugs can be detected compared to a central CodeChecker report database.  

Let's assume that you are working on the master branch and the analysis of the master branch
is store already under run name ``tmux_master``.

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
 CodeChecker cmd diff -b tmux_master -n ./reports --new --host codechecker.central --port 8555
```

