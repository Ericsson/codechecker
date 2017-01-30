# Running performance tests

### 1. Build a package

See main readme how to do it.

### 2. Start the server with a check-port

```
CodeChecker server -w workspace --postgresql --check-port 10001 --view-port 10002
```

### 3. Create a test configuration file similar to this:

If the performance test is started with multiple processes with the `-j` flag each process will
generate and measure based on the test configuration.  
Each process will generate, store and measure the configured number of runs and results.

`number_of_runs`: how many runs should be generated  
`file_line_size`: how many line should be in the generated dummy source file  
`number_of_files`: how many source files should be generated  
`bug_per_file`: bug count in one file  
`bug_length`: bug path length for each bug  
`clean_after_fill`: remove all run results after each measurement  
`wait_for_store`: if multiple processes are used for measurement wait until the database is filled up with dummy results before starting the measurements  
`check_port`: the check port used in the CodeChecker server command  
`view_port`: the view port used in the CodeChecker server command  

A test configuration cloud look like this:  
```
{
  "number_of_runs" : 1,
  "file_line_size" : 100,
  "number_of_files" : 100,
  "bug_per_file" : 8,
  "bug_length" : 5,
  "clean_after_fill" : true,
  "wait_for_store" : true,
  "host" : "localhost",
  "check_port" : 10001,
  "view_port" : 10002
}
```

### 4. Run the performance test

Activate virtualenv
~~~~~~{.sh}
source ~/checker_env/bin/activate
~~~~~~

The test result will be generated to the `test_results` directory in cvs format.

```
./run_performance_test -o test_results --test-config perf_test.conf -j 4
```
