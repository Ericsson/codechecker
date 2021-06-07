# Mac OS X Installation Guide

In OSX environment the intercept-build tool from
[scan-build](https://github.com/rizsotto/scan-build) is used to log the
compiler invocations.

It is possible that the [intercept-build can not
log](https://github.com/rizsotto/scan-build#limitations)
the compiler calls without turning off *System Integrity Protection (SIP)*.
`intercept build` can automatically detect if SIP is turned off.

You can turn off SIP on El Capitan this way:

  * Click the  (Apple) menu.
  * Select Restart...
  * Hold down command-R to boot into the Recovery System.
  * Click the Utilities menu and select Terminal.
  * Type csrutil disable and press return.
  * Close the Terminal app.
  * Click the  (Apple) menu and select Restart....

The following commands are used to bootstrap CodeChecker on
OS X El Capitan 10.11, macOS Sierra 10.12 and macOS High Sierra 10.13.

```sh
# Download and install dependencies.
brew update
brew install gcc git
pip3 install virtualenv

# Install the latest clang see: https://formulae.brew.sh/formula/llvm
brew install llvm@10.0.0

# Install npm
brew install npm

# Fetch source code.
git clone https://github.com/Ericsson/CodeChecker.git --depth 1 ~/codechecker
cd ~/codechecker

# Create a Python virtualenv and set it as your environment.
make venv_osx
source $PWD/venv/bin/activate

# Build and install a CodeChecker package.
make package

# For ease of access, add the build directory to PATH.
export PATH="$PWD/build/CodeChecker/bin:$PATH"

cd ..
```
