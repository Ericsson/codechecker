#!/bin/bash

if [ "$(id -u)" == '0' ]; then
  # Change the owner of the user-mounted directories
  mkdir -p /project /workspace
  chown codechecker:codechecker /project /workspace

  # Execute this script again with codechecker user.
  exec gosu codechecker "$0" "$@"
fi

exec "$@"
