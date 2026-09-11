FROM ubuntu:26.04

# Install Thrift version 0.22 from Ubuntu repositories.
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y thrift-compiler && \
    rm -rf /var/lib/apt/lists/
