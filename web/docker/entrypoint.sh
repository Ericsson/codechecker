#!/bin/bash

USER_ID=$($USER)
USER_GROUP="$(id -g)"
WORKSPACE_DIR="/workspace"
PGPASS_FILE=$WORKSPACE_DIR/.pgpass

if [ "$(id -u)" = '0' ]; then
  # Create workspace directory and change the permission to 'codechecker' user
  # if this directory doesn't exists.
  if [ ! -d $WORKSPACE_DIR ]; then
    mkdir -p $WORKSPACE_DIR
    chown -R codechecker:codechecker $WORKSPACE_DIR
  fi

  # Execute this script again with codechecker user.
  exec gosu codechecker "$0" "$@"
fi

# Set PostgreSQL password file from secrets.
pgpass=/run/secrets/pgpass
if [ -f $pgpass ]; then
  cat $pgpass > ${PGPASS_FILE}
  chmod 0600 ${PGPASS_FILE}
  chown ${USER_ID}:${USER_GROUP} ${PGPASS_FILE}
  export PGPASSFILE=${PGPASS_FILE}
fi

exec "$@"
