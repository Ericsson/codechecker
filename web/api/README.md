# CodeChecker server Thrift API

This directory contains the API IDL files and the generated API stubs for
CodeChecker. [Apache Thrift](https://thrift.apache.org/) is used to generate
the stubs for various programming languages (Python, JavaScript).

The Thrift compiler is executed inside a [Docker](https://www.docker.com/)
container so `docker` needs to be installed to generate the stubs.

## API change workflow:

Assuming the current api version is **6.24.0** and no breaking change was
introduced.

### How to modify the API
- Modify the `.thrift` API files.
- Check the current API version in one of the following files:
  - [`py/codechecker_api/setup.py`](py/codechecker_api/setup.py)
  - [`py/codechecker_api_shared/setup.py`](py/codechecker_api_shared/setup.py)
  - [`js/codechecker-api-node/package.json`](js/codechecker-api-node/package.json)
- Let's assume that the current API version is `6.39.0`. Run the
[change-api-version.sh](change-api-version.sh) script to increment the API
version: `change-api-version.sh 6.40.0`.
- Update the supported api versions to `6.40` in the server files:
  - `web/codechecker_web/shared/version.py`
  - `web/server/vue-cli/config/webpack.common.js`
- Run the command `make build` to generate the Thrift API stubs and to create
new pypi and npm packages. It will modify the following files:
  - [`py/codechecker_api/dist/codechecker_api.tar.gz`](py/codechecker_api/dist/codechecker_api.tar.gz)
  - [`py/codechecker_api_shared/dist/codechecker_api_shared.tar.gz`](py/codechecker_api_shared/dist/codechecker_api_shared.tar.gz)
  - [`js/codechecker-api-node/dist/codechecker-api-x.y.z.tgz`](js/codechecker-api-node/dist/)
- Run `make clean_package && make package` in the root directory of this
repository to create a new CodeChecker package and see whether the new API
works properly.
