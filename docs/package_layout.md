# CodeChecker package builder

Short description for the package layout of the generic CodeChecker package.
Package creation is based on the package layout config file.
It has two main parts a static and a runtime part.

### External checker libraries
External checker libraries can be used in the package. The shared object files
should be in the plugin directory and will be automatically loaded at runtime.

## Runtime section
The runtime part contains information which will be used only at runtime
to find files during the checking process.
