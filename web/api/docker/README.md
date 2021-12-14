# Docker image for Thrift
Unforunately the [official docker image](https://hub.docker.com/_/thrift) what
we used during development is deprecated and doesn't have an image for latest
thrift versions. For this reason we will build our own image
(`codechecker/thrift`) based on docker file from
[here](https://github.com/ahawkins/docker-thrift/blob/master/0.12/Dockerfile).

## Build docker image
Use the following commands to build and publish docker image for Thrift from
the root directory of this repository:
```sh
# Build docker image.
docker build \
  --build-arg THRIFT_VERSION=v0.15.0 \
  --tag codechecker/thrift:0.15.0 \
  --file web/api/docker/thrift.Dockerfile \
  web/api/docker/

# Publish docker image.
docker push codechecker/thrift:0.15.0
```
