#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
    DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"


export CC_LOGGER_GCC_LIKE="gcc:g++:clang"
export CC_LOGGER_JAVAC_LIKE=""
export CC_PACKAGE_ROOT=$(dirname $DIR)
unset  CODECHECKER_ALCHEMY_LOG
export PATH=$CC_PACKAGE_ROOT/bin:$PATH

