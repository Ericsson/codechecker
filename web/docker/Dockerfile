###############################################################################
#-----------------------------    BUILD STAGE   ------------------------------#
###############################################################################

FROM python:3.6-slim-stretch as builder

ARG CC_VERSION=master
ENV CC_VERSION ${CC_VERSION}

COPY hooks/ /hooks

ARG DEBIAN_FRONTEND=noninteractive
RUN set -x && apt-get update -qq \
  && apt-get install -qqy --no-install-recommends \
    ca-certificates \
    curl \
    git \
    make \
    && curl -sL https://deb.nodesource.com/setup_12.x | bash - \
    && apt-get install -y nodejs

# Download CodeChecker release.
RUN git clone https://github.com/Ericsson/CodeChecker.git /codechecker
WORKDIR /codechecker
RUN git checkout ${CC_VERSION}

# Run script before the package generation.
RUN chmod a+x /hooks/before_build.sh && sync && /hooks/before_build.sh

# Build CodeChecker web.
RUN make -C /codechecker/web package

# Run script after the package generation is finished.
RUN chmod a+x /hooks/after_build.sh && sync && /hooks/after_build.sh

###############################################################################
#--------------------------    PRODUCTION STAGE   ----------------------------#
###############################################################################

FROM python:3.6-slim-stretch

ARG CC_GID=950
ARG CC_UID=950

ENV CC_GID ${CC_GID}
ENV CC_UID ${CC_UID}

ARG INSTALL_AUTH=yes
ARG INSTALL_PG8000=no
ARG INSTALL_PSYCOPG2=yes

ENV TINI_VERSION v0.18.0
ENV WAIT_FOR_VERSION v2.1.2

RUN set -x && apt-get update -qq \
  # Prevent fail when install postgresql-client.
  && mkdir -p /usr/share/man/man1 \
  && mkdir -p /usr/share/man/man7 \
  \
  && apt-get install -qqy --no-install-recommends ca-certificates \
    postgresql-client \
    # To switch user and exec command.
    gosu

RUN if [ "$INSTALL_AUTH" = "yes" ] ; then \
      apt-get install -qqy --no-install-recommends \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev; \
    fi

RUN if [ "$INSTALL_PSYCOPG2" = "yes" ] ; then \
      apt-get install -qqy --no-install-recommends \
        libpq-dev; \
    fi

COPY --from=builder /codechecker/web/build/CodeChecker /codechecker

# Copy python requirements.
COPY --from=builder /codechecker/web/requirements_py /requirements_py
COPY --from=builder /codechecker/web/requirements.txt /requirements_py

# Copy local API packages (Python, Node).
COPY --from=builder /codechecker/web/api /api

# Install python requirements.
RUN apt-get update -qq  && \
  apt-get install -qqy --no-install-recommends \
    python3-dev \
    # gcc is needed to build psutil.
    gcc \
    # netcat is needed for 'wait-for' script.
    netcat \
  \
  # Install necessary runtime environment files.
  && pip3 install -r /requirements_py/requirements.txt \
  && if [ "$INSTALL_AUTH" = "yes" ] ; then \
       pip3 install -r /requirements_py/auth/requirements.txt; \
     fi \
  && if [ "$INSTALL_PG8000" = "yes" ] ; then \
       pip3 install -r /requirements_py/db_pg8000/requirements.txt; \
     fi \
  && if [ "$INSTALL_PSYCOPG2" = "yes" ] ; then \
       pip3 install -r /requirements_py/db_psycopg2/requirements.txt; \
     fi \
  \
  # Remove unnecessary packages.
  && pip3 uninstall -y wheel \
  && apt-get purge -y --auto-remove \
    gcc \
    python-dev \
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
RUN chmod 755 /tini

ADD https://raw.githubusercontent.com/eficode/wait-for/${WAIT_FOR_VERSION}/wait-for /usr/local/bin/wait-for
RUN chmod 755 /usr/local/bin/wait-for

EXPOSE 8001

ENTRYPOINT ["/tini", "--", "/usr/local/bin/entrypoint.sh"]

CMD ["CodeChecker", "server", "--workspace", "/workspace", "--not-host-only"]
