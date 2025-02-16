#!/bin/bash

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install \
  docker \
  gcc \
  llvm \
  cppcheck \
  openssl \
  postgresql
#  libldap2-dev \
#  libsasl2-dev \
#  libssl-dev \
#  libpq-dev

# Need to add clang to the path beacuse brew wont override the system clang
#ln -s /usr/local/opt/llvm/bin/clang-tidy /usr/local/bin/clang-tidy
#ln -s /usr/local/opt/llvm/bin/clang /usr/local/bin/clang
