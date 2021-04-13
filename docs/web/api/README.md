# Thrift API
These APIs should be used by the clients connecting to the server to store and
get results.

Any new client should only interact with the database through these APIs.

# Table of Contents
* [Available APIs](#available-apis)
    * [Report server](#report-server-api)
    * [Authentication system](#authentication-system-api)
    * [Product management system](#product-management-system-api)
* [API versioning](#api-versioning)
    * [How to add new API versions](#how-to-add-new-api-versions)
        * [Minor API improvements](#minor-api-improvements)
        * [Major API changes](#major-api-changes)
    * [How to delete API versions](#how-to-delete-api-versions)

# Available APIs <a name="available-apis"></a>

## Report server API <a name="report-server-api"></a>
The report server API should be used by any client to view or store analysis
results.

## Authentication system API <a name="authentication-system-api"></a>
The authentication layer is used for supporting privileged-access only access
and permission management.

## Product management system API <a name="product-management-system-api"></a>
The product management layer is responsible for handling requests about the
different products and their configuration.

# API versioning <a name="api-versioning"></a>

CodeChecker supports some backward compatibility between API versions.

The API version is automatically encoded into the `POST` request URLs made by
Thrift in the following format:

    http://example.com:8001/[product-name]/<API-version>/<API-service>

For example:

    https://example.com:8001/Default/v6.0/CodeCheckerService

Executing `make thrift` in the web folder of CodeChecker will automatically
build each API version to the `build/` dir.

## How to add new API versions <a name="how-to-add-new-api-versions"></a>

### Minor API improvements <a name="minor-api-improvements"></a>

For minor changes, these changes should go into the **existing** API files,
with appropriate Thrift-based versioning for `struct`s where necessary.

Minor version changes should not change the behaviour and the invocation of
already existing functions, only extend the API:

 1. After implementing the changes to the existing API files and handlers,
 you need to increase the `SUPPORTED_VERSIONS` tag in
 `codechecker_web/shared/version.py`. This dict stores for each major
 version, which is the highest supported minor version. In this case, simply
 increase the number by `1`.

### Major API changes <a name="major-api-changes"></a>

For major changes, a **new** API must be defined. Start by creating a full
copy of the previous version's API to a new folder, e.g. `v7`.

> **NOTE!** Make sure the `Authentication` service API contains the
> `checkAPIVersion` function. Each client is expected to call this function to
> test if the server accepts its version.

 1. The new API definition (`thrift`) files must have the `namespace` tag
 appropriately suffixed, e.g. `_v7`.
 2. Register a new *major* version in the `SUPPORTED_VERSIONS` dict in
 `codechecker_web/shared/version.py`, but do **NOT** change the previous
 major version's setting. The first *minor* version for every *major* version
 is `0`, i.e. `7.0`.
 3. Change the `server/www/scripts/version.js` to use the newest API, `7.0` in
 this case.
 4. Change the imports used in `server/www/scripts/<site>/<site>.js` (`<site>`
 is `codecheckerviewer` or `productlist`) to load the API client from the new
 version. Do the same with the Python code everywhere (including the tests)
 where API clients are used (`client/codechecker_client`).
 5. Implement requesting actions via the new API in the command-line and the
 Web client.
 6. In the server, implement the API handlers for the new version **as
 separate** Python modules.
 7. `import` these new API handlers to the server module, and in the `do_POST`
 method of the server, set up that API requests through *major* version `7`
 are routed to be handled by these new handlers. (Keep the formatting of
 imported names akin to those already in the file.)

## How to delete API versions <a name="how-to-delete-api-versions"></a>

Only major API versions can be deleted.

 1. Remove the `thrift` API definition's folder from under `api`.
 2. Delete the API handler code from the server's files, and the routing
 declarations in the `do_POST` method.
 3. In the `version.py`, remove this *major* version's entry from the
 `SUPPORTED_VERSIONS` table.
