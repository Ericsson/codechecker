#!/bin/bash

make venv_dev && \
source venv_dev/bin/activate && \
make pycodestyle pylint package test_unit test_functional
