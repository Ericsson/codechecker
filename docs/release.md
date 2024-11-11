# CodeChecker release
If CodeChecker is released on the GitHub we need to create new docker images
and a new snap package from it.

## How to create a new docker image
A Github action will automatically create docker images on every new release.
If you would like to build docker images manually from a CodeChecker repository
run the following commands (don't forget to replace `<x.y>` with the new
version):
```sh
# Checkout the new release.
git checkout v6.<x.y>

# Build the image without cache.
docker build \
  --build-arg CC_VERSION=v6.<x.y> \
  --tag codechecker/codechecker-web:6.<x.y> \
  --no-cache \
  web/docker

# Update the latest tag.
docker build \
  --build-arg CC_VERSION=v6.<x.y> \
  --tag codechecker/codechecker-web:latest \
  web/docker
```

## How to create a new snap package
To build and release a snap package from a new CodeChecker version do the
following steps:

1. Check and update the `version` and the `source` values in the
`snap/snapcraft.yaml` file with the version you would like to build for a new
CodeChecker snap package.
2. Run the following commands from a CodeChecker repository:

    ```sh
    # Clean the previous builds.
    snapcraft clean

    # Build the snap package.
    snapcraft

    # Try out the package in your local environment.
    sudo snap install codechecker_<version>_amd64.snap --dangerous --classic

     # See if it works.
    snap run codechecker version

    # Login to the snap store.
    snapcraft login

    # Upload and release it to the stabel channel.
    snapcraft upload --release=stable codechecker_<version>_amd64.snap

    # Get info from the revisions.
    snapcraft list-revisions codechecker

    # Update the package on my machine.
    sudo snap refresh codechecker --stable --classic --amend

    # See if it works.
    snap run codechecker version
    ```
