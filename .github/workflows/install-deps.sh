#!/bin/bash

wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key|sudo apt-key add -
sudo add-apt-repository 'deb http://apt.llvm.org/focal/ llvm-toolchain-focal-14 main' -y
# Required for g++-13, as the latest LTS at the time of this change hasn't made it available.
sudo add-apt-repository -y ppa:ubuntu-toolchain-r/test

sudo apt-get update -q

sudo apt-get install \
  g++-13 \
  gcc-multilib \
  libc6-dev-i386 \
  libpq-dev \
  libldap2-dev \
  libsasl2-dev \
  libssl-dev \
  clang-14 \
  clang-tidy-14 \
  cppcheck

# Source: https://fbinfer.com/docs/getting-started
VERSION=1.2.0; \
curl -sSL "https://github.com/facebook/infer/releases/download/v$VERSION/infer-linux-x86_64-v$VERSION.tar.xz" \
| sudo tar -C /opt -xJ && \
sudo ln -s "/opt/infer-linux-x86_64-v$VERSION/bin/infer" /usr/local/bin/infer

sudo update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-14 9999
sudo update-alternatives --install /usr/bin/clang clang /usr/bin/clang-14 9999
sudo update-alternatives --install /usr/bin/clang-tidy clang-tidy /usr/bin/clang-tidy-14 9999
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 9999
