#!/bin/bash

if [ "$(id -u)" == '0' ]; then
  # Set PostgreSQL password file from secrets.
  pgpass=/run/secrets/pgpass
  if [ -f $pgpass ]; then
    cp $pgpass /.pgpass
    chmod 0600 /.pgpass
    chown codechecker:codechecker /.pgpass
    export PGPASSFILE=/.pgpass
  fi

  # Change the owner of the workspace directory
  mkdir -p /workspace
  chown codechecker:codechecker /workspace

  # Execute this script again with codechecker user.
  exec gosu codechecker "$0" "$@"
fi

exec "$@"
