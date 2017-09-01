
# Thrift APIs
These APIs should be used by the clients using the database to store or to get the results. Any new client should only interact with the database through these APIs.

## Report server API
The report server API should be used by any client to view or store check results.
See [report_server.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/api/report_server.thrift).

## Authentication system API
The authentication layer is used for supporting privileged-access only access.
See [authentication.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/thrift_api/authentication.thrift)

## Product management system API
The product management layer is responsible for handling requests about the
different products and their configuration. See
[products.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/thrift_api/products.thrift)