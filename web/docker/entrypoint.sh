#!/bin/bash

USER_ID="$(id -u)"
USER_GROUP="$(id -g)"
WORKSPACE_DIR="/workspace"
PGPASS_FILE=$WORKSPACE_DIR/.pgpass

if [ "$USER_ID" = '0' ]; then
  echo "Container started with 'root' user."

  if [ -d $WORKSPACE_DIR ]; then
    echo "Workspace directory '${WORKSPACE_DIR}' already exists."

    workspace_dir_owner=$(stat ${WORKSPACE_DIR} -c %u)
    if [ "${workspace_dir_owner}" != '0' ]; then
      echo "Executing script with workspace directory owner (UID): '${workspace_dir_owner}'..."
      exec gosu $workspace_dir_owner "$0" "$@"
    fi
  else
    echo "Creating workspace directory: '${WORKSPACE_DIR}'."
    echo "WARNING: This directory exists ONLY within the containter!"

    mkdir -p $WORKSPACE_DIR
    chown -R codechecker:codechecker $WORKSPACE_DIR

    echo "Executing script with internal 'codechecker' user (UID: $(id -u codechecker))..."
    exec gosu codechecker "$0" "$@"
  fi
fi

pgpass=/run/secrets/pgpass
if [ -f $pgpass ]; then
  echo "Set PostgreSQL password file from secrets."
  cat $pgpass > ${PGPASS_FILE}
  chmod 0600 ${PGPASS_FILE}
  chown ${USER_ID}:${USER_GROUP} ${PGPASS_FILE}
  export PGPASSFILE=${PGPASS_FILE}
fi

echo "Executing command: '$@'."
exec "$@"
