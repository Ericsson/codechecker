#!/bin/bash

#--- Initialize environment ---#

logger_dir=$1

export LD_PRELOAD=ldlogger.so
export LD_LIBRARY_PATH=$logger_dir/lib:$LD_LIBRARY_PATH
export CC_LOGGER_GCC_LIKE="gcc:g++:clang"
export CC_LOGGER_FILE=/tmp/logger_test_compilation_database.json

source_file=/tmp/logger_test_source.cpp
reference_file=/tmp/logger_test_reference.json

function assert_json {
  cat > $reference_file << EOF
[
	{
		"directory": "$(pwd)",
		"command": "$(readlink -f $(which $2)) $1",
		"file": "$source_file"
	}
]
EOF

  sed -i -e '$a\' $CC_LOGGER_FILE

  diff $reference_file $CC_LOGGER_FILE
}

#--- Test functions ---#

function test_simple {
  bash -c "g++ $source_file"

  assert_json "$source_file" g++
}

function test_cpath {
  CPATH=path1 \
  bash -c "g++ $source_file"

  assert_json \
    "-I path1 $source_file" \
    g++
}

function test_cpath_after_last_I {
  CPATH=":path1:path2:" \
  bash -c "g++ -I p0 $source_file -I p1 -I p2"

  assert_json \
    "-I p0 $source_file -I p1 -I p2 -I . -I path1 -I path2 -I ." \
    g++
}

function test_cplus {
  CPLUS_INCLUDE_PATH="path1:path2" \
  C_INCLUDE_PATH="path3:path4" \
  bash -c "g++ -I p0 -isystem p1 $source_file"

  assert_json \
    "-I p0 -isystem p1 -isystem path1 -isystem path2 $source_file" \
    g++
}

function test_c {
  CPLUS_INCLUDE_PATH="path1:path2" \
  C_INCLUDE_PATH="path3:path4" \
  bash -c "gcc -I p0 -isystem p1 $source_file"

  assert_json \
    "-I p0 -isystem p1 -isystem path3 -isystem path4 $source_file" \
    gcc
}

function test_cpp {
  CPLUS_INCLUDE_PATH="path1:path2" \
  C_INCLUDE_PATH="path3:path4" \
  bash -c "gcc -I p0 -isystem p1 -x c++ $source_file"

  assert_json \
    "-I p0 -isystem p1 -isystem path1 -isystem path2 -x c++ $source_file" \
    gcc
}

#--- Run tests ---#

echo "int main() {}" > $source_file

for func in $(declare -F); do
  if [[ $func =~ test_ ]]; then
    rm -f $CC_LOGGER_FILE
    $func

    if [ $? -ne 0 ]; then
      echo Test failed: $func
      rm a.out
      exit 1
    fi
  fi
done

rm a.out
