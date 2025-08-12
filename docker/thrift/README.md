# Thrift builder docker

## How to build
```bash
docker build -t thrift:<version> -f Dockerfile.thrift.noble .
```

## How to use
This image should be used like an executable. Input files are provided via mounting a directory.
Here's an example of compiling `authentication.thrift` to python.

```bash
docker run --rm -v "$(pwd):/data" thrift:<version> thrift -r -o /data --gen py --gen js:node /data/authentication.thrift
```
