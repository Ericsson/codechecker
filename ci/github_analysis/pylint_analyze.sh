#!/bin/bash

pylint --version
disabled_checkers="duplicate-code,fixme,consider-using-get,too-many-instance-attributes"
pylint --rcfile=.pylintrc -j0 --disable $disabled_checkers -f json --output ./pylint-reports.json ./build/CodeChecker/lib/python3/*
