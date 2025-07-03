#!/bin/bash

CC_URL="https://codechecker-demo.eastus.cloudapp.azure.com/codechecker"

./ci/github_analysis/pylint_analyze.sh

report-converter -c -t pylint -o ./reports-pylint ./pylint-reports.json
CodeChecker version
CodeChecker store ./reports-pylint --url "$CC_URL" --trim-path-prefix "$(pwd)" -n master
new_finding_count=$(CodeChecker cmd results --url "$CC_URL" master --detection-status 'NEW' 'REOPENED' --review-status 'UNREVIEWED' 'CONFIRMED' | grep -c "NEW\|REOPENED")
if [ "$new_finding_count" -ne "0" ]; then
   echo "ERROR. This PUSH introduced $new_finding_count new findings to the master branch! Please check them at $CC_URL/reports?review-status=Unreviewed&review-status=Confirmed%20bug&detection-status=New&run=master&is-unique=off&diff-type=New"
   exit 1
else
   echo "SUCCESS. No new reports introduced"
   exit 0
fi
