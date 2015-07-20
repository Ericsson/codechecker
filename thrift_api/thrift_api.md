
#Thrift APIs
These APIs should be used by the clients using the database to store or to get the results. Any new client should only interact with the database through these APIs.

## Report viewer server API
The report viewer server API should be used by any client to view the check results.
See [report-viewer-server.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/thrift-api/report-viewer-server.thrift).

## Report storage server API
The report storage server API is used internally in the package during runtime to store the results to the database.
See [report-storage-server.thrift](https://raw.githubusercontent.com/Ericsson/codechecker/master/thrift-api/report-storage-server.thrift).
