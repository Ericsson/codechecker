# Python client for CodeChecker
`client.py` contains simple API requests to a CodeChecker server and it
can be a starting point for writing your own script.

Before you run this example program you have to do the following steps to
setup an environment:

```sh
# Create a Python virtualenv and set it as your environment.
python3 -m venv venv
source $PWD/venv/bin/activate

# Install thrift package.
pip3 install thrift==0.21.0

# Get and install CodeChecker API packages.
#
# It will download API packages for the 'v6.19.1' but you can download newer
# versions as well.
#
# WARNING: make sure that the package versions are not newer than what
# CodeChecker server uses.
wget https://github.com/Ericsson/codechecker/raw/v6.19.1/web/api/py/codechecker_api/dist/codechecker_api.tar.gz && \
pip3 install codechecker_api.tar.gz && \
rm -rf codechecker_api.tar.gz

wget https://github.com/Ericsson/codechecker/raw/v6.19.1/web/api/py/codechecker_api_shared/dist/codechecker_api_shared.tar.gz && \
pip3 install codechecker_api_shared.tar.gz && \
rm -rf codechecker_api_shared.tar.gz
```

After your environment is ready you can run the following command:

```sh
python3 client.py \
  --protocol "http" \
  --host "localhost" \
  --port 8001 \
  --username "codechecker" \
  --password "admin"
```