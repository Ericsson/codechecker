#!/bin/bash

CC_URL="https://codechecker-demo.eastus.cloudapp.azure.com/codechecker"

if [ "$#" -ne 1 ]; then
    echo "<PR_NAME> is missing"
fi

./ci/github_analysis/pylint_analyze.sh
report-converter -c -t pylint -o ./reports-pylint ./pylint-reports.json
CodeChecker cmd diff --url "$CC_URL" -b master -n ./reports-pylint --new
if [ "$?" -ne 0 ]; then
    echo "ERROR. YOUR PR FAILED GATING!"
    exit 1
else
    echo "Gating successful. No new report found. Your PR is ready to be merged."
fi