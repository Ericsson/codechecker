#CodeChecker command line examples
###1.	Check the project, overwrite any earlier results and view results from command line
```
CodeChecker quickcheck -b make
  
#runs check and shows the result on command line
```
###2.	Check a project, update earlier results  and view results from a browser
Runs make, logs build, run analyzers and store the results
```
CodeChecker check -b make
```
  
  Start webserver, which listens on default port localhost:8001 
  results can be viewed in a browser
```
CodeChecker server
```
  
  The developer may also suppress false positives
  At the end, the project is rechecked 
```
CodeChecker check make
```
###3. Same as use case 2., but the developer would like to enable alpha checkers from clang-sa, and llvm checkers from clang-tidy
```
CodeChecker check –e alpha -e llvm -b make
```
###4.	Same as use case 2., but the developer stores suppressed false positives in a text file that is checked in into version control
```
CodeChecker check –u /home/myuser/myproject/suppress.list -b make
CodeChecker server –u /home/myuser/myproject/suppress.list

#suppress list will be stored in suppress.list with the bug hashes in the file
#the user checks in the suppress.list file with the source code
```
###5.	Same as use case 2., but the developer wants to give extra Config to clang-tidy or clang-sa
```
CodeChecker check --saargs clangsa.config --tidyargs clang-tidy.config -b make

#clang-sa and clang-tidy parameters are stored in simple text files, 
#is expected to be in the same format as clang-sa/tidy 
#command line parameters and will be passed to every clang-sa/tidy calls
```

###6.	Asking for command line help for the check subcommand (all other subcommands would be the same: server, checkers,cmd…)
```
CodeChecker check -h
```


###7.	Run analysis on 2 versions of the project
Analyze a large project from a script/Jenkins job periodically. Developers view the results on a central web-server.
If a hit is false positive, developers can mark it and comment it on the web interface and the suppress hashes are stored in a text file that can be version controlled.
Different versions of the project can be compared for new/resolved/unresolved bugs. Differences between runs can be viewed in the web browser or from command line (and can be sent in email if needed).

Large projects should use postgresql for performance reasons.

```
CodeChecker check -n myproject_v1 –postgresql -b make
CodeChecker check -n myproject_v2 –postgresql -b make

#runs analysis, assumes that postgres is available on the default 5432 TCP port, 
#codechecker db user exists and codechecker can be created
#stores results in postgres in a db called codechecker under name myproject_v1,myproject_v2
#please note that this use case is also supported with SQLITE db
```

###8.	Start the webserver and view the diff between the two results in the web browser
```
CodeChecker server –postgresql

#assumes that postgres is available on the default 5432 TCP port, 
#codechecker db user exists and codechecker db is used

firefox localhost:8001

#webserver listens on port 8001 and user can see the diff of the runs in a browser
```
###9.	Start the webserver and view the diff between the two results in command line
```
CodeChecker cmd diff –b myproject_v1 –n myproject_v2 –p 8001 -new

#assumes that the server is started on port 8001 (as specificed in step 5) 
#then shows the new bugs in myproject_v2 compared to baseline myproject_v1

CodeChecker cmd diff –b myproject_v1 –n myproject_v2 –p 8001 -unresolved

#assumes that the server is started on port 8001 (as specificed in step 5) 
#then shows the unresolved bugs in myproject_v2 compared to baseline myproject_v1

CodeChecker cmd diff –b myproject_v1 –n myproject_v2 –p 8001 -resolved

#assumes that the server is started on port 8001 (as specificed in step 5)
#then shows the resolved bugs in myproject_v2 compared to baseline myproject_v1
```
###10.	Start the webserver with a suppress file
```
CodeChecker server –u suppress.file -postgresql

#web server is listening on port 8001; False positives can be suppressed in the
#Web interface and the bug hash of the suppressed bugs are stored in the suppress.file
#suppress.file can be stored in the version control
```
