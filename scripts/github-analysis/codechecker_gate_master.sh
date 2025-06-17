#!/bin/bash
./scripts/github-analysis/pylint_analyze.sh
report-converter -c -t pylint -o ./reports-pylint ./pylint-reports.json
CodeChecker store ./reports-pylint --url https://codechecker-demo.eastus.cloudapp.azure.com/codechecker --trim-path-prefix `pwd` -n master
new_findings=`CodeChecker cmd results --url https://codechecker-demo.eastus.cloudapp.azure.com/codechecker/ master --detection-status 'NEW' 'REOPENED' --review-status 'UNREVIEWED' 'CONFIRMED'|grep "NEW\|REOPENED"|wc -l`
if [ "$new_findings" -ne "0" ]; then
   echo "ERROR. This PUSH introduced $new_findings new findings to the master branch! Please check them at https://codechecker-demo.eastus.cloudapp.azure.com/codechecker/reports?review-status=Unreviewed&review-status=Confirmed%20bug&detection-status=New&run=master&is-unique=off&diff-type=New"
   exit 1 
else
   echo "SUCCESS. No new reports introduced"
fi




