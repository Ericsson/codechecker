#!/bin/bash
pylint --version
disabled_checkers="--disable duplicate-code --disable fixme --disable consider-using-get --disable too-many-instance-attributes"
pylint --rcfile=.pylintrc -j0 --ignore=migrations ./build/CodeChecker/lib/python3/* --enable all $disabled_checkers -f json --output ./pylint-reports.json

