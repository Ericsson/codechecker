#!/bin/bash

pylint --version

ROOT=$(pwd)

JSON_DIR='reports/'
mkdir -p $JSON_DIR

WORKDIR="$ROOT"/analyzer/tools/merge_clang_extdef_mappings
pylint --rcfile="$WORKDIR"/.pylintrc -f json --output $JSON_DIR/pylint-reports-clang.json -j0 --py-version=3.10 \
    "$WORKDIR"/codechecker_merge_clang_extdef_mappings \
    "$WORKDIR"/tests/**

WORKDIR="$ROOT"/analyzer/tools/statistics_collector
pylint --rcfile="$WORKDIR"/.pylintrc -f json --output $JSON_DIR/pylint-reports-statictics-collector.json -j0 --py-version=3.10 \
    "$WORKDIR"/codechecker_statistics_collector \
    "$WORKDIR"/tests/**


WORKDIR="$ROOT"/web
pylint --rcfile="$WORKDIR"/../.pylintrc -f json --output $JSON_DIR/pylint-reports-web.json -j0 --py-version=3.10 \
    --ignore="$WORKDIR"/server/codechecker_server/migrations/report,"$WORKDIR"/server/codechecker_server/migrations/report/versions,"$WORKDIR"/server/codechecker_server/migrations/config,"$WORKDIR"/server/codechecker_server/migrations/config/versions \
    "$WORKDIR"/codechecker_web \
    "$WORKDIR"/client/codechecker_client \
    "$WORKDIR"/server/codechecker_server \
    "$WORKDIR"/server/tests/unit \
    "$WORKDIR"/tests/functional \
    "$WORKDIR"/tests/libtest \
    "$WORKDIR"/tests/tools \
    "$WORKDIR"/../tools/report-converter/codechecker_report_converter

WORKDIR="$ROOT"
pylint --rcfile="$WORKDIR"/.pylintrc -f json --output $JSON_DIR/pylint-reports-root.json -j0 --py-version=3.10 \
    "$WORKDIR"/bin/** \
    "$WORKDIR"/codechecker_common \
    "$WORKDIR"/scripts/** \
    "$WORKDIR"/scripts/build/** \
    "$WORKDIR"/scripts/debug_tools/** \
    "$WORKDIR"/scripts/resources/** \
    "$WORKDIR"/scripts/test/** \
    "$WORKDIR"/scripts/thrift/**

jq -s 'add' $JSON_DIR/* > pylint-reports.json
