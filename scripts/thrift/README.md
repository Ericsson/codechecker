# Python client for CodeChecker
`client.py` contains simple API requests to a CodeChecker server and it
can be a starting point for writing your own script.

Before you run this example program you have to do the following steps to
setup an environment:

```sh
# Create a Python virtualenv and set it as your environment.
python3 -m venv venv
source $PWD/venv/bin/activate

# Install the thrift package.
pip3 install thrift==0.22.0
```

The `codechecker_api` Python stubs are generated from the `.thrift` API
description files in the `codechecker_api/` directory by a Thrift compiler that
runs inside a Docker container, so `docker` needs to be installed on your
system.

Running `make package` (or `make dev_package`) in the root of the repository
generates the stubs into `codechecker_api/python/`:

```sh
make package
```

> **NOTE:** The API version used by the client is hard-coded in `client.py`
> (the `CLIENT_API` constant). Make sure that the API version is not newer than
> what the CodeChecker server uses.

After your environment is ready you can run the following command:

```sh
python3 scripts/thrift/client.py \
  --protocol "http" \
  --host "localhost" \
  --port 8001 \
  --username "codechecker" \
  --password "admin"
```
