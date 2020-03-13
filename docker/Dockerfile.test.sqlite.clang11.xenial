FROM ubuntu:16.04

RUN apt-get update \
  && apt-get install -y \
    software-properties-common \
    wget \
    apt-transport-https \
    ca-certificates \
  && wget -qO - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - \
  && add-apt-repository "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-11 main" \
  && apt-get update \
  && apt-get install --no-install-recommends -y \
       clang-11 \
       clang-tidy-11 \
       libpq-dev \
       make \
       build-essential \
       curl \
       gcc-multilib \
       git \
       python3-virtualenv \
       python-virtualenv \
       python3-dev \
       python3-pip \
       python3-setuptools \
       libsasl2-dev \
       libldap2-dev \
       libssl-dev \
  && pip3 install wheel \
  && pip3 install virtualenv \
  && update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-11 9999 \
  && update-alternatives --install /usr/bin/clang clang /usr/bin/clang-11 9999 \
  && update-alternatives --install /usr/bin/clang-tidy clang-tidy /usr/bin/clang-tidy-11 9999

COPY . /codechecker

WORKDIR "/codechecker"

RUN chmod a+x /codechecker/docker/entrypoint.sh

ENTRYPOINT ["/codechecker/docker/entrypoint.sh"]
