Table of Contents
=================
* [How to build a new debian package](#how-to-build-a-new-debian-package)
* [Install CodeChecker debian package](#install-codechecker-debian-package)
  * [Install gdebi](#install-gdebi)
  * [Install the package](#install-the-package)
  * [Reinstall CodeChecker debian package](#reinstall-codechecker-debian-package)

# How to build a new debian package
* Upgrade **Version** in the `debian/DEBIAN/conffiles`.
* Create a new entry in `debian/DEBIAN/changelog` which includes modifications
made in the Debian package compared to the upstream one as well as other changes
and updates to the package. For more information see:
https://www.debian.org/doc/debian-policy/#debian-changelog-debian-changelog
* Build the package: `make deb`

# Install CodeChecker debian package
## Install gdebi
Install `gdebi` command which is a great tool to install packages and their
dependencies:

```bash
sudo apt-get install gdebi
```

## Install the package
```bash
sudo gdebi ./codechecker.deb
```

# Reinstall CodeChecker debian package
```bash
sudo apt-get --reinstall install ./codechecker.deb
```
