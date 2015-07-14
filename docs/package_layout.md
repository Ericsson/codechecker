# Codechecker package builder

Short description for the package layout of the generic codechecker package.
Package creation is based on the package layout config file.
It has two main parts a static and a runtime part.

## Static section
Static part is used to create the main package skeleton (directory structure) where the CodeChecker finds the required files.

### External checker libraries
External checker libraries can be used in the package. The shared object files should be in the plugin directory and will be automatically loaded at runtime.

## Runtime section
The runtime part contains informations which will be used only at runtime
to find files during the checking process.
