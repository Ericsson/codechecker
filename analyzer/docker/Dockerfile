###############################################################################
#-----------------------------    BUILD STAGE   ------------------------------#
###############################################################################

FROM python:3.6-slim-stretch as builder

ARG CC_VERSION=master
ENV CC_VERSION ${CC_VERSION}

ARG DEBIAN_FRONTEND=noninteractive
RUN set -x && apt-get update -qq \
  && apt-get install -qqy --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    doxygen \
    gcc-multilib \
    git

# Download CodeChecker release.
RUN git clone https://github.com/Ericsson/CodeChecker.git /codechecker
WORKDIR /codechecker
RUN git checkout ${CC_VERSION}

# Build CodeChecker web.
RUN make -C /codechecker/analyzer package

###############################################################################
#--------------------------      OBTAIN   LLVM    ----------------------------#
###############################################################################

FROM alpine:3.12.0 as llvmfetch

RUN apk add -qf --no-progress \
  wget

RUN wget -qO - http://api.github.com/repos/llvm/llvm-project/releases/latest \
    # Get the link for the binary release for an Ubuntu.
    | grep "clang%2Bllvm-"       \
    | grep "$(arch)"             \
    | grep "ubuntu"              \
    | grep -v "sig"              \
    | cut -d ":" -f 2,3          \
    | sed -E 's/^ "(.*)",?$/\1/' \
    # Actually download the file. LLVM binary builds are huge, show progress
    # but don't flood the console with a lot of progress dots! 8M seems fine
    # for ~600 MiB downloads.
    | wget --progress=dot -e dotbytes=8M \
      -O llvm.tar.xz -i -   \
  && tar xf llvm.tar.xz \
  && mv clang+llvm* llvm \
  && rm llvm.tar.xz

###############################################################################
#--------------------------    PRODUCTION STAGE   ----------------------------#
###############################################################################

FROM python:3.6-slim-stretch

ARG CC_GID=950
ARG CC_UID=950

ENV CC_GID ${CC_GID}
ENV CC_UID ${CC_UID}

ENV TINI_VERSION v0.18.0

RUN set -x && apt-get update -qq \
  && apt-get install -qqy --no-install-recommends \
    # To switch user and exec command.
    gosu

COPY --from=builder /codechecker/analyzer/build/CodeChecker /codechecker

# Copy python requirements.
COPY --from=builder /codechecker/analyzer/requirements_py /requirements_py
COPY --from=builder /codechecker/analyzer/requirements.txt /requirements_py

# Copy binary LLVM release.
COPY --from=llvmfetch /llvm /llvm
ENV PATH="/llvm/bin:$PATH"

# Install python requirements.
RUN apt-get install -qqy --no-install-recommends \
  python3-dev \
  # gcc is needed to build psutil.
  gcc \
  \
  # Install necessary runtime environment files.
  && pip3 install -r /requirements_py/requirements.txt \
  # Remove unnecessary packages.
  && pip3 uninstall -y wheel \
  && apt-get purge -y --auto-remove \
    gcc \
    python3-dev \
  \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/ \
  && set +x

# Create user and group for CodeChecker.
RUN groupadd -r codechecker -g ${CC_GID} \
  && useradd -r --no-log-init -M -u ${CC_UID} -g codechecker codechecker

# Change permission of the CodeChecker package.
RUN chown codechecker:codechecker /codechecker

ENV PATH="/codechecker/bin:$PATH"

COPY ./entrypoint.sh /usr/local/bin/
RUN chmod a+x /usr/local/bin/entrypoint.sh \
  && chown codechecker:codechecker /usr/local/bin/entrypoint.sh

ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

ENTRYPOINT ["/tini", "--", "/usr/local/bin/entrypoint.sh"]

CMD ["CodeChecker", "analyzers", "--details", "--output", "table"]
