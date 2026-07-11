#!/bin/bash
set -euo pipefail

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

# Facebook Infer has no Homebrew formula on current macOS runners,
# but provides prebuilt binaries on GitHub releases.
# Source: https://github.com/facebook/infer/releases
INFER_VERSION=1.3.0
ARCH=$(uname -m)
curl -sSL "https://github.com/facebook/infer/releases/download/v${INFER_VERSION}/infer-osx-${ARCH}-v${INFER_VERSION}.tar.xz" \
  | sudo tar -C /opt -xJ
sudo ln -sf "/opt/infer-osx-${ARCH}-v${INFER_VERSION}/bin/infer" /usr/local/bin/infer
infer --version

# Homebrew's llvm@14 does not know where the macOS SDK lives, so libc++
# headers that use '#include_next <ctype.h>' (and other platform C headers)
# fail with "file not found". Apple's own clang resolves this via xcrun, but
# the standalone llvm@14 needs SDKROOT to be set explicitly. Recent runner
# images removed the implicit header path clang@14 used to fall back on,
# which is why analyzer and web tests started failing with:
#   fatal error: 'ctype.h' file not found
# Pin SDKROOT to the active SDK so subsequent build and test steps can compile.
if [ -n "$GITHUB_ENV" ]; then
  echo "SDKROOT=$(xcrun --show-sdk-path)" >> "$GITHUB_ENV"
  # Restrict native builds to the host arch. clang@14 does not support
  # universal2 builds against the current macOS SDK.
  echo "ARCHFLAGS=-arch $(uname -m)" >> "$GITHUB_ENV"
  # gcc@13 defaults to an older deployment target than the installed SDK, so
  # the Xcode toolchain's (clang-based) assembler prints
  #   "clang: warning: overriding deployment version ... [-Woverriding-deployment-version]"
  # to stderr. The GCC analyzer uses '-fdiagnostics-format=sarif-stderr', so
  # this warning is appended to the SARIF stream and makes it invalid JSON
  # (breaking analyze_and_parse's gcc tests). Pin the deployment target to the
  # SDK version so no override (and no warning) is emitted.
  echo "MACOSX_DEPLOYMENT_TARGET=$(xcrun --show-sdk-version)" >> "$GITHUB_ENV"
  # Build pip C extensions (e.g. python-ldap) with Apple's clang, not the
  # Homebrew llvm@14 clang that this script puts on PATH for the analyzer.
  # clang@14 cannot link against the current macOS SDK's TBD libraries
  # (e.g. 'ld: library ldap_r not found'), whereas Apple clang handles the
  # SDK natively. CodeChecker selects its analyzer binary independently of
  # $CC, so this does not affect which compiler is analyzed/used as analyzer.
  echo "CC=/usr/bin/clang" >> "$GITHUB_ENV"
  echo "CXX=/usr/bin/clang++" >> "$GITHUB_ENV"
fi
