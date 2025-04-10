# CodeChecker server Thrift API

This directory contains the API IDL files and the generated API stubs for
CodeChecker. [Apache Thrift](https://thrift.apache.org/) is used to generate
the stubs for various programming languages (Python, JavaScript).

The Thrift compiler is executed inside a [Docker](https://www.docker.com/)
container so `docker` needs to be installed to generate the stubs.

## API change workflow:
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
- Run the command `make build` to generate the Thrift API stubs and to create
new pypi and npm packages. It will modify the following files:
  - [`py/codechecker_api/dist/codechecker_api.tar.gz`](py/codechecker_api/dist/codechecker_api.tar.gz)
  - [`py/codechecker_api_shared/dist/codechecker_api_shared.tar.gz`](py/codechecker_api_shared/dist/codechecker_api_shared.tar.gz)
  - [`js/codechecker-api-node/dist/codechecker-api-x.y.z.tgz`](js/codechecker-api-node/dist/)
- Run `make clean_package && make package` in the root directory of this
repository to create a new CodeChecker package and see whether the new API
works properly.
- Before commit make sure to add new pypi/npm package files to git.

WARNING: when you want to modify the thrift file again with the same version
number and regenerate the local packages you may have to reset the changes
made in the `package-lock.json` file so `npm` will be able to detect the
package change. For this you can use the following commands from the repository
root folder:
```sh
git checkout master -- web/server/vue-cli/package-lock.json
git reset HEAD web/server/vue-cli/package-lock.json
```
# Codechecker OAuth developer documentation

  * Important: To maintain consistency between GitHub and other providers, we need to fetch primary email
  from another endpoint because GitHub dosn't provide the primary email in the `user_info`,so
  we make an API request to fetch the primary email of the GitHub and use it instead of the username provided by the `user_info`.

  * Github doesn't support PKCE and If GitHub starts supporting PKCE in the future, the code should automatically
  start using it ,and in that case, this note can be removed.

  * Important: for different providers there are different requirements for providing refresh token.

    In case of of google you need to specify these 2 attributes `access_type='offline'` and `prompt='consent'` prompts `google` to return `refresh_token`.

    ```
    access_type='offline',
    prompt='consent'
    ```

    This is not required for Github and Microsoft and causes Microsoft to request unnecessary admin priveleges.
    The same effect can be reproduced for Microsoft , by adding `offline_access` in scope.
    Whereas GitHub return refresh token by default.

```.py
  if provider == "google":
              url, state = session.create_authorization_url(
                  url=authorization_url,
                  state=stored_state,
                  code_verifier=pkce_verifier,
                  access_type='offline',
                  prompt='consent'
              )
          else:
              url, state = session.create_authorization_url(
                  authorization_url,
                  state=stored_state,
                  code_verifier=pkce_verifier
              )
```