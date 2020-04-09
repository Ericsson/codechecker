# CodeChecker server Thrift API

This directory contains the API IDL files and the generated API stubs for
CodeChecker. [Apache Thrift](https://thrift.apache.org/) is used to generate
the stubs for various programming languages. The stubs are published to
[pypi](https://pypi.org/) and to [npmjs](https://www.npmjs.com/).

The Thrift compiler is executed inside a [Docker](https://www.docker.com/)
container so docker needs to be installed to generate the stubs.

## API change workflow:

Assuming the current api version is **6.24.0** and no breaking change was
introduced.

### 1. Modify the Thrift files.

- Update the versions in the **setup.py** files to **6.24.0-dev1**.
  - `py/codechecker_api/setup.py`
  - `py/codechecker_api_shared/setup.py`
- Update the versions in the **package.json** files to **6.24.0-dev1**.
  - `js/codechecker-api-js/package.json`
  - `js/codechecker-api-node/package.json`

- Publish the packages:
  - If you have access to publish packages to pypi and npm do the following:
    - Run the command `make build` to generate the stubs.

    - Publish python dev versions:
      - `make publish_py`
    - Publish javascript dev versions with the `dev` tag:
      - `make publish_js_dev`
  - If you do not have access to publish the packages, create a pull request
    on github, wait while it will be reviewed, merged and someone will create
    the packages for you.
- In the `setup.py` and `package.json` files use the **6.24.0-dev1** version
until the api is accepted.

### 2. Server/client implementation for the API change

- Update the *requirements.txt* and the **web/server/vendor/Makefile**.
- Remove the old files, update the venv and rebuild the package:
  ```sh
  rm -rf web/server/vendor/codechecker-api-js/ && \
  rm -rf venv_dev && make venv_dev && \
  make clean_package && make package
  ```
- Extend the server with the new API functionality with the dev API versions
  as a dependency.
- Create a pull request with the changes.
- Wait while it will be reviewed and approved.

### 3. API change was approved

- After API change approval increment the api versions to **v6.25.0**
in the setup.py and package.json files.
- Publish the **v6.25.0** packages to pypi and npm.
- Update the latest tag in npmjs for the published packages:
  - `npm dist-tag add codechecker-api@6.25.0 latest`
  - `npm dist-tag add codechecker-api-js@6.25.0 latest`

### 4. Update the Server/client implementation

- Update the **requirements.txt** files and the **web/server/vendor/Makefile**
in the pull request to use the new client stubs with version **v6.25.0**.
- Update the supported api versions to **v6.25** in the server files:
  - `web/codechecker_web/shared/version.py`
  - `web/server/www/scripts/version.js`

### 5. Mark the development packages as deprecated on pypi and npmjs
