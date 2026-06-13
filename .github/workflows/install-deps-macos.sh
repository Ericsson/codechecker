#!/bin/bash

brew install llvm@14 gcc@13 cppcheck openldap bear

echo "$(brew --prefix llvm@14)/bin" >> "$GITHUB_PATH"
echo "$(brew --prefix gcc@13)/bin" >> "$GITHUB_PATH"

# Create g++ symlink matching Linux CI naming
GCC_BIN="$(brew --prefix gcc@13)/bin"
ln -sf "$GCC_BIN/g++-13" "$GCC_BIN/g++"
ln -sf "$GCC_BIN/gcc-13" "$GCC_BIN/gcc"

# Create intercept-build wrapper using bear.
# The LLVM intercept-build is broken on macOS ARM64 (libear.dylib arch
# mismatch with SIP). Bear provides equivalent functionality.
WRAPPER_DIR="$(pwd)/build/intercept-build-wrapper"
mkdir -p "$WRAPPER_DIR"
cat > "$WRAPPER_DIR/intercept-build" << 'EOF'
#!/bin/bash
CDB=""
CMD=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cdb) CDB="$2"; shift 2 ;;
        --help) echo "intercept-build wrapper using bear"; exit 0 ;;
        *) CMD+=("$1"); shift ;;
    esac
done
[[ -z "$CDB" ]] && CDB="compile_commands.json"
exec bear --output "$CDB" -- "${CMD[@]}"
EOF
chmod +x "$WRAPPER_DIR/intercept-build"
echo "$WRAPPER_DIR" >> "$GITHUB_PATH"
