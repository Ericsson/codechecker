
#Thrift APIs
These APIs should be used by the clients using the database to store or to get the results. Any new client should only interact with the database through these APIs.

## Report viewer server API
The report viewer server API should be used by any client to view the check results.
See [report_viewer_server.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/thrift_api/report_viewer_server.thrift).

## Report storage server API
The report storage server API is used internally in the package during runtime to store the results to the database.
See [report_storage_server.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/thrift_api/report_storage_server.thrift).

## Authentication system API
The authentication layer is used for supporting privileged-access only access.
See [authentication.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/thrift_api/authentication.thrift)