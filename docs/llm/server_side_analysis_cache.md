# Design document of the CodeChecker remote analysis cache

This is a specification of the CodeChecker analysis cache functionality as an MVP.
The cache functionality will be provided by the server as a new thrift service called `AnalysisCache`, defined in `codechecker_api/analysis_cache.thrift`.
The analysis results will be stored in a bazel-remote backend.
In this MVP, the caching is restricted to the clang static analyzer executions, but later should be extensible to other analyzers.

## Server Interface
- implement it in thrift as a new service `AnalysisCache` in the new file `codechecker_api/analysis_cache.thrift`
- the API follows the conventions of the existing CodeChecker thrift APIs: camelCase function names, errors are reported by throwing `shared.RequestFailed`

### Thrift api specification

```thrift
// codechecker_api/analysis_cache.thrift

include "shared.thrift"

namespace py codechecker_api.python.AnalysisCache_v6
namespace js codeCheckerAnalysisCache_v6

struct CacheContent {
  1: string filename,  // Role of the file in the cached result (e.g. the
                       // result file, stdout, stderr). Plain basename only,
                       // it must not be used as a file system path.
  2: string content,   // base64(zlib(file bytes))
}
typedef list<CacheContent> CacheContents

service AnalysisCache {

  // Store the given files for the given analysis key.
  // Returns true if the files were stored.
  bool writeCache(1: string        key,
                  2: CacheContents contents)
                  throws (1: shared.RequestFailed requestError),

  // Return the files stored for the given analysis key.
  // In case of a cache miss an empty list is returned.
  CacheContents readCache(1: string key)
                          throws (1: shared.RequestFailed requestError),
}
```

- the file content is transferred as `base64(zlib(file bytes))`, the same encoding as the one used by `massStoreRun`; plist result files compress well (typically 5-10x), so this keeps the request size of large (up to 10 MB) result files small

### Integration of the new endpoint
- `web/server/codechecker_server/server.py` (`RequestHandler.do_POST`): add a dispatch branch for the `AnalysisCache` request endpoint, which requires a product route (raise `ProductNotFoundError` if there is no product, like `CodeCheckerService`), and creates the new handler with `AnalysisCache_v6.Processor`
- `web/server/codechecker_server/routing.py`: add `"AnalysisCache"` to `NON_PRODUCT_ENDPOINTS`, so that no product can be created with this endpoint name
- `codechecker_api/Makefile`: add `analysis_cache.thrift` to the `thrift_stubs` target, and regenerate the Python and JS stubs
  - the stubs are generated with the `thrift_compiler` Docker image of `codechecker_api/Makefile` (`make -C codechecker_api build_codechecker_api`); the generated `codechecker_api/python/AnalysisCache_v6` and `codechecker_api/js` stubs are committed, like the existing ones
- bump the API minor version: 6.74 → 6.75 (`codechecker_api/api_version.json`)

## Specification of the server implementation

- the thrift endpoint should be product specific like the report_server endpoint. thus, to access the api, the url must contain the product endpoint: `<server>/<product>/v<api version>/AnalysisCache`.
- all api request should require the PRODUCT_CACHE permission (see Permission).
- the API does not provide delete operations; outdated entries are removed by the LRU eviction of bazel-remote (`--max_size`). The cache size limit is global for the bazel-remote instance, there is no per product cache size limit.

### Permission
- a new product level permission `PRODUCT_CACHE` is added
  - `codechecker_api/shared.thrift`: new value in `enum Permission`: `PRODUCT_CACHE = 20, // scope: PRODUCT`
  - `web/server/codechecker_server/permissions.py`:
    ```python
    PRODUCT_CACHE = _create_permission(ProductPermission, 'PRODUCT_CACHE',
                                       default_enable=False,
                                       managed_by=[PRODUCT_ADMIN])
    ```
- `PRODUCT_CACHE` is the only permission of the analysis cache API: both writeCache and readCache require it
- no other permission inherits it: it is not granted automatically by `PRODUCT_ADMIN`, `PRODUCT_STORE`, `PRODUCT_ACCESS` or `PRODUCT_VIEW` (`inherited_from` is empty); it must be granted explicitly to the users / groups which may use the cache
  - the only exception is `SUPERUSER`, which is hardcoded in `Permission.__init__` to inherit every permission
- `PRODUCT_CACHE` is managed by the product admins (`managed_by=[PRODUCT_ADMIN]`, and implicitly `SUPERUSER`), like the other product permissions
- every API call checks the permission for the requested product; a missing permission is reported with `RequestFailed` (`ErrorCode.UNAUTHORIZED`)
- if authentication is disabled on the server, the permission check passes for everyone, like for the other product permissions
- config database migration:
  - product permissions are stored in the config database as an SQL enum (type `product_perms`, column `permissions_product.permission`), so the new permission requires a new Alembic migration in `web/server/codechecker_server/migrations/config/versions/`
  - the migration follows `126fa3f55e4b_added_permission_for_product_view.py`: on PostgreSQL the enum type is renamed, recreated with the new value and the column is converted; on SQLite the column is altered with `batch_alter_table`; the downgrade removes the value
  - `PRODUCT_CACHE` is also added to the enum of the ORM model of the config database
  - existing servers must upgrade the config database schema (`CodeChecker server --db-upgrade-schema` or the automatic upgrade at startup); without it, granting `PRODUCT_CACHE` fails on PostgreSQL

### Cache key
- the user provided analysis_key is not used directly as a bazel-remote key; the server computes the bazel-remote Action Cache (AC) key by hashing the product endpoint name into the key:
  - `ac_key = sha256("<product endpoint>:<analysis_key>")`, as a 64 character lowercase hex string
- this avoids cache sharing between products: the same analysis_key in two products results in two different AC keys
- the product name is hashed into the key instead of being added as a plain prefix, because bazel-remote accepts only sha256 hex strings (64 hex characters) as keys

### Storage format in bazel-remote
- the server stores the cache entries in the standard Bazel Remote Execution API (REAPI) format:
  - every file of the cache entry is stored in the Content Addressable Storage (CAS): `PUT /cas/<sha256 of the stored content>`
  - the stored content is the base64(zlib()) encoded file content exactly as it was received on the thrift API; it is returned unchanged by readCache, so the server neither re-encodes nor transfers the larger uncompressed form to/from bazel-remote, which keeps the network bandwidth low
  - the AC entry is a serialized REAPI `ActionResult` protobuf message: `PUT /ac/<ac_key>`
    - every file is an `OutputFile` entry in `ActionResult.output_files`, with `path` = the `filename` of the `CacheContent` and `digest` = (sha256 hash, size in bytes) of the stored (encoded) content in the CAS
    - `exit_code` = 0 (only successful analyses are cached)
- bazel-remote validates the uploaded `ActionResult` messages (the default behavior); it must not be started with `--disable_http_ac_validation`
- protobuf dependency:
  - add the `protobuf` Python package to the server requirements (`web/requirements.txt`, using a compatible version range like the other dependencies, e.g. `protobuf~=6.0`)
  - only the `Digest`, `OutputFile` and `ActionResult` messages of the REAPI are needed: a reduced copy of `build/bazel/remote/execution/v2/remote_execution.proto` with these messages (with the same package name, field names and field numbers, so it is wire compatible) is added to the server, and its generated Python module is committed; gRPC is not needed, the server uses only the HTTP API of bazel-remote

### writeCache(analysis_key, contents)
1. validate the input (see Input validation); the content is not decompressed on the server
2. compute the sha256 digest and size of every encoded file content
3. upload every encoded file content into the CAS
4. only after all CAS uploads succeeded, upload the `ActionResult` into the AC with the ac_key; this order makes sure that an AC entry never refers to a missing CAS blob at the time of writing
5. return true if all uploads succeeded; if the bazel-remote backend is not available or returns an error, throw `RequestFailed` (`ErrorCode.IOERROR`)

### readCache(analysis_key)
1. validate the analysis_key (see Input validation)
2. download the AC entry `GET /ac/<ac_key>`; on HTTP 404 return an empty list (cache miss)
3. parse the `ActionResult`; if it cannot be parsed or fails the validation, log a warning and return an empty list (cache miss)
4. download every referenced CAS blob `GET /cas/<sha256>`; if any blob is missing (HTTP 404, e.g. it was evicted by the LRU while the AC entry was kept), return an empty list (cache miss); partial results are never returned
5. verify that the sha256 and size of every downloaded blob match the digest in the `ActionResult`; on mismatch return an empty list (cache miss)
6. return the files as `CacheContent` entries with `filename` = `OutputFile.path` and `content` = the stored base64(zlib()) encoded content, unchanged
- if the bazel-remote backend is not available or returns an unexpected error, throw `RequestFailed` (`ErrorCode.IOERROR`); the client treats this as a cache miss

### Input validation
Every invalid request is rejected with `RequestFailed` (`ErrorCode.GENERAL`) and a message describing the problem; nothing is written into the cache in this case.
- `key` (writeCache, readCache):
  - exactly 64 characters, lowercase hex digits only (`^[0-9a-f]{64}$`), i.e. a sha256 hex digest
- `contents` (writeCache):
  - not empty
  - at most `max_files_per_entry` entries (server config, default: 16)
  - the `filename` values are unique within the request
- `filename`:
  - matches `^[A-Za-z0-9._-]{1,255}$` (a plain basename: no path separators `/` or `\`, no whitespace or control characters)
  - not `.` or `..`
- `content`:
  - valid base64 (strict decoding, invalid characters are rejected)
  - the server does not decompress the content and does not verify the decompressed size; it only limits the size of the received (encoded) content: at most `max_file_size` per file (server config, default: 20 MiB) and at most `max_entry_size` for all files of the request (server config, default: 50 MiB)
- `ActionResult` read from bazel-remote (readCache): it is validated with the same `filename` rules and digest format (64 hex characters) as the writeCache input; an invalid entry is handled as a cache miss
- decompression is the client's responsibility, the client validates the readCache response:
  - it accepts only the expected file roles (result file, stdout, stderr)
  - it decodes the base64 content, and decompresses the zlib stream incrementally with an output size limit (`zlib.decompressobj().decompress(data, max_length)`), so a highly compressed input (zip bomb) is rejected before it is fully decompressed into memory; a response exceeding the limit is handled as a cache miss
  - it writes the cached result only into the report directory, to its own computed output path (see the client side implementation)

### Server configuration
- the codechecker server should connect to the bazel-remote with http or with https with optional basic authentication
- the following bazel-remote access configuration parameters must be added to codechecker's server_config.json
  - bazel-remote url
  - bazel-remote user
  - bazel-remote password file
  - cache timeout: timeout of the cache connect+read/write
  - input validation limits: `max_files_per_entry`, `max_file_size`, `max_entry_size`
- the configuration block in `server_config.json` (with the default values):
  ```json
  "analysis_cache": {
    "url": "https://bazel-remote:8080",
    "user": null,
    "password_file": null,
    "timeout": 30,
    "max_files_per_entry": 16,
    "max_file_size": 20971520,
    "max_entry_size": 52428800
  }
  ```
  - `user` / `password_file`: optional basic authentication; the password is read from the file, it is not stored in `server_config.json`
  - `timeout`: seconds, used for connect and read/write of every bazel-remote request
  - `max_file_size`, `max_entry_size`: bytes, limits of the encoded content (see Input validation)
- if the `analysis_cache` block is missing (or has no `url`), the cache is not configured: writeCache and readCache throw `RequestFailed` (`ErrorCode.GENERAL`, message `analysis cache is not configured`); the client handles it as a cache miss and continues the analysis
- HTTPS certificate verification uses the system CA bundle (see Future work for custom CA support)


## Specification of the Client side implementation:
- add the analysis cache access before the clang static analyzer analysis invocation in codechecker
- analysis cache workflow
  - before the analysis invocation check wether the analysis is cached by the readCache() function
  - if there was a cache hit, write out the returned files to the same location as the original analysis invocation would have written
  - if there is a cache miss, execute the analysis and in case of successful analysis store the output into the cache using the writeCache thrift function
- cache the raw analyzer output, not the post-processed result
  - after the analyzer run, CodeChecker modifies the result file depending on settings which are not part of the cache key:
    - `ClangSA.post_analyze()` removes the reports of disabled checkers (disabled checkers are not passed to clang, so they are not in the analysis invocation string)
    - `ResultHandler.postprocess_result()` applies skip list filtering, review status filtering and report hash rewriting (`--report-hash`), and `error_file.update()` adds analyzer info into the result file
  - caching the post-processed file would therefore return wrong results for runs with the same cache key but with different `--disable`, skip file, review status or report hash settings
  - cache miss:
    - run the analysis as before (`source_analyzer.analyze()`)
    - if the analyzer return code is 0 (and the analysis did not time out), read the raw result file (`rh.analyzer_result_file`) and the analyzer stdout/stderr immediately after `analyze()` returns, before `post_analyze()` is called
    - store these raw outputs into the cache with writeCache
    - continue with the unchanged post-processing path (`post_analyze()` → `handle_success()`)
  - cache hit:
    - write the cached raw result file to `rh.analyzer_result_file`
    - set `rh.analyzer_cmd` to the constructed analyzer command, `rh.analyzer_returncode = 0`, and `rh.analyzer_stdout` / `rh.analyzer_stderr` from the cached content
    - skip the analyzer invocation and continue with the same post-processing path as a successful analysis (`post_analyze()` → `handle_success()`), so the current run's checker, skip, review status and report hash settings are applied to the cached result
  - the client must write the cached result only to its own computed output path (`rh.analyzer_result_file`); the files returned by the server are identified by their role (result file, stdout, stderr), the server-provided filename must not be used as a file system path
- protection against local path traversal: cached content may be written only into the report directory (the `--output` directory of `CodeChecker analyze`)
  - the cache content is never written to a path derived from server provided data; the target path is always computed locally (`rh.analyzer_result_file`)
  - before writing, the target path is resolved with `os.path.realpath()` and must be inside the resolved report directory (`os.path.commonpath([real_target, real_report_dir]) == real_report_dir`); otherwise the entry is not written, and it is handled as a cache miss with a warning
  - the target file must not be a symbolic link (an existing symlink in the report directory could point outside of it); the file is first written to a temporary file in the report directory, and then moved to the target path with `os.replace()`, which replaces the symlink itself and does not follow it
  - cached stdout / stderr are not written to files directly; they are set into the result handler (`rh.analyzer_stdout`, `rh.analyzer_stderr`) and written by the existing post-processing code (e.g. `--capture-analysis-output`), into the report directory
- the client side checks are implemented in the central cache library, so that every analyzer plugin uses the same protection
- in the readCache, writeCache operations use this key: `analysis_id_key = sha256("v1:" + analysis_invocation_key + ":" + preprocessed_source_key + ":" + analyzer_binary_key)`
  - `v1` is the version of the cache entry format; bumping it invalidates all existing entries (e.g. if the format of the cached content changes), as the API has no delete operation
- the files of a cache entry are identified by fixed role names in `CacheContent.filename`:
  - `result.plist`: the raw analyzer result file
  - `stdout.txt`: the analyzer stdout
  - `stderr.txt`: the analyzer stderr
  - on readCache, the client ignores any other filename; an entry without `result.plist` is a cache miss
- client side limits and timeouts:
  - decompressed size limit: 20 MiB per file (zip bomb protection, see Input validation)
  - AnalysisCache API timeout: 5 s connect, 30 s read
- the preprocessed_source_key and the analyzer_binary_key should be computed by a central CodeChecker library which can be accessed by all analyzer plugins.
- The analysis_invocation_key should be calculated locally in the analyzer plugin.
- In case of clang static analyzer, the analysis_invocation_key should be (analysis invocation string) eg ("/usr/bin/clang --analyze -Qunused-arguments -Xclang -analyzer-output=plist-multi-file -o /workspace/test-projects/tinyxml2/reports/xmltest.cpp_clangsa_3e85aaf332fe01343c3163ef26e631f7.plist -Xclang -analyzer-config -Xclang expand-macros=true -Xclang -analyzer-checker=core.BitwiseShift,core.CallAndMessage,core")
  - the invocation string is `shlex.join()` of the analyzer command list (with the `-o` value replaced, see below), so the quoting of the arguments is unambiguous
- in this first prototype we don't want to rewrite the absolute paths to relative paths. we will handle that in a later iteration.
- the output file path must be removed from the analysis_invocation_key
  - the `-o <result file>` argument is an output location, not an analysis input; it contains the report directory, so different report directories (users, CI workspaces) would otherwise never get a cache hit, even for identical analyses
  - when computing the analysis_invocation_key, replace the value of the `-o` argument with a fixed placeholder (e.g. `-o <OUTPUT>`); the real command line used for the analysis is not changed
  - this is not path rewriting: all other absolute paths (source file, include paths, etc.) remain in the key unchanged
- the analyzer_binary_key is computed from the analyzer version, not from the binary file
  - analyzer_binary_key = sha256(<full output of `<analyzer binary> --version`>)
  - the configured analyzer binary can be a compiler wrapper (e.g. `/usr/lib/ccache/clang` → ccache); hashing the binary file would identify the wrapper instead of clang, while `--version` is forwarded by the wrapper to the real clang, so it identifies the real analyzer
  - the full `--version` output is used (not only the version number), because it also contains the vendor, the source revision and the default target
  - the analyzer_binary_key is computed only once per `CodeChecker analyze` run in the main process and passed to the analysis worker processes
- the preprocessed_source_key is computed from the output of a dedicated preprocessor command
  - the ClangSA plugin provides a separate `construct_preprocess_cmd()` method next to `construct_analyzer_cmd()`, built from the same parts of the analyzer command which influence preprocessing:
    - analyzer binary, `-E`, `-x <language>`, `-arch` (if any), analyzer extra arguments, the build action's analyzer options (defines, include paths, etc.), `--target`, `-std`, the compiler implicit include directories (`-idirafter` / `-isystem`), and the source file
  - not included: `--analyze`, the `-Xclang -analyzer-*` options, plugin loading options and the `-o <result file>` argument; the preprocessed output is streamed into the hash, it is not written to a file
  - the preprocessor command must run in the same working directory (`buildaction.directory`) and with the same environment as the analyzer command, otherwise relative include paths and environment variables (e.g. `CPATH`) could produce a different preprocessed output
  - preprocessing runs before every cache lookup, so it also adds to the runtime on cache hits; its overhead should be measured on a reference project
  - if preprocessing fails, the action is analyzed without the cache (no readCache, no writeCache)
- CodeChecker analyze command line arguments must be extended with an optional --url parameter. The url must contain a codechecker server product endpoint which will be used for accessing the AnalysisCache api. e.g https://codechecker.gic.ericsson.se/Test
- add also --no-cache parameter which switches off the caching. By specifying --url caching is automatically turned on.
  - both `--url` and `--no-cache` are added to `CodeChecker analyze` (`analyzer/codechecker_analyzer/cli/analyze.py`) and to `CodeChecker check` (`analyzer/codechecker_analyzer/cli/check.py`), which forwards them to the analysis
- after each analysis print a small statistics about how many analysis actions were successfully fetched from the cache
  - `check()` in `analysis_manager.py` returns a tuple which is unpacked by `worker_result_handler()`; it is extended with a `cache_hit` field, also in the exception path of `check()`
  - `worker_result_handler()` counts the cache hits, and prints them in the summary, e.g. `Fetched from analysis cache: 42 / 50`

### Package boundary
- the analyzer package (`codechecker_analyzer`) does not depend on `thrift` and `codechecker_client` (web package), and it can be built and used standalone
- the cache client code which uses the web client (thrift) is imported lazily, only if caching is turned on
- if `--url` is given, but the web client is not available (analyzer only installation), `CodeChecker analyze` stops with a clear error message before the analysis starts

### Authentication and multiprocessing
- the analysis runs in a pool of worker processes; the existing `codechecker_client.client.setup_client()` can prompt for a password and calls `sys.exit()` on authentication failure, which must not happen inside a worker process
- therefore authentication is done once, in the main process, before the worker pool is started:
  - the main process sets up the connection to the product's AnalysisCache endpoint, authenticates (using the stored credentials / session token, like `CodeChecker store`), and checks that the product is reachable
  - the session token and the connection parameters are passed to the workers in the pool initializer (`init_worker`)
  - if the authentication or the connection check fails, a warning is printed and the analysis continues without the cache
- every worker process creates its own thrift client lazily, at the first cache access; thrift clients are not shared between processes (they cannot be pickled)

### Fail open
- the cache must never break or block the analysis: any cache or network error (connection error, timeout, `RequestFailed`, invalid response) is handled as a cache miss, and logged on debug level
- after N consecutive cache errors (e.g. 3) in a worker process, the worker stops using the cache for the rest of the run, so an unavailable server does not add a timeout to every analysis action
- a failed writeCache does not affect the result of the analysis

### What is written into the cache
- only analyses which were successful are written into the cache:
  - the analyzer return code is 0
  - the analysis did not time out (`--timeout`)
  - CTU analysis was not active for the action (see Future work: the CTU result depends on other TUs which are not part of the key); for CTU actions neither readCache nor writeCache is called

## Testing
- there is no bazel-remote in the test environment; the tests use a mock bazel-remote server
  - a small HTTP server implemented in the test suite (Python `http.server`, started in a thread or process by the test setup) which implements the used part of the bazel-remote HTTP API:
    - `PUT /cas/<sha256>`: stores the blob, rejects it with HTTP 400 if the sha256 of the body does not match the key
    - `GET /cas/<sha256>`: returns the blob or HTTP 404
    - `PUT /ac/<key>`: parses the body as an `ActionResult` (with the same protobuf module as the server), rejects it with HTTP 400 if it cannot be parsed or if a referenced CAS blob is missing; this mimics the AC validation of bazel-remote
    - `GET /ac/<key>`: returns the entry or HTTP 404
    - optional basic authentication check
    - test hooks to delete single CAS blobs (to simulate the LRU eviction) and to return errors / delays (to simulate an unavailable backend)
  - the mock does not reproduce every detail of bazel-remote (e.g. LRU eviction, compression); the compatibility with a real bazel-remote has to be checked manually before the release
- unit tests:
  - server: input validation (key, filenames, base64, size limits), AC key computation (product hashing), `ActionResult` building and parsing, readCache miss cases (AC 404, missing CAS blob, digest mismatch, invalid `ActionResult`)
  - client: key computation (`-o` placeholder, `shlex.join`, version prefix), decompression limit, path traversal protection (target outside the report directory, symlink target), role filtering, fail open behavior
- functional tests (`web/tests/functional/`), with a CodeChecker server configured to use the mock bazel-remote:
  - permission: calls without `PRODUCT_CACHE` are rejected, calls with it succeed
  - product isolation: the same key in two products does not share the entry
  - end to end: `CodeChecker analyze --url` on a small test project; the first run writes the cache (0 hits), the second run fetches all actions from the cache and produces the same reports as the first run
  - `--no-cache`, server without cache configuration, unavailable mock backend: the analysis succeeds without the cache

## Documentation updates
- `docs/analyzer/user_guide.md`: the new `--url` and `--no-cache` options of `CodeChecker analyze` and `CodeChecker check`, the cache statistics in the summary, and the conditions when the cache is (not) used (successful, non-timed out, non-CTU ClangSA analyses)
- `docs/web/server_config.md`: the new `analysis_cache` block of `server_config.json`, and the required bazel-remote setup (validation of the AC entries must stay enabled, the `--max_size` option controls the cache size)
- `docs/web/permissions.md`: the new `PRODUCT_CACHE` permission (it is not inherited from other product permissions, it must be granted explicitly)
- `docs/web/db_schema_guide.md` / upgrade notes: the config database schema upgrade for the new permission

## Future work

### Custom CA certificate for bazel-remote
- the MVP verifies the HTTPS certificate of bazel-remote with the system CA bundle only
- later: add an optional `ca_file` option to the `analysis_cache` block of `server_config.json`, to support a bazel-remote with a certificate issued by an internal CA; disabling the certificate verification should not be supported

### Analysis inputs not covered by the cache key

Some inputs change the analysis result, but in the MVP only their paths (or flags) appear in the analysis invocation string, not their content. Including them in the cache key is not part of the MVP implementation. Until they are handled, a cache hit may return a stale result when only the content of these inputs changed (the paths and flags stayed the same).

| Input | What is in the key now | Future handling |
|---|---|---|
| CTU analysis (`-analyzer-config ctu-dir=…`, `ctu-invocation-list=…`) | the CTU directory path only; the result also depends on the ASTs / sources of other TUs | in the MVP caching is disabled for CTU analyses; later: extend the key with the hash of all involved TUs |
| Statistics based checkers (`stats_cfg` from `SpecialReturnValueCollector`) | the statistics directory path only | add the hash of the statistics files' content to the key |
| ClangSA checker plugins (`-load <plugin>.so`) | the plugin paths only | add the hash of the plugin `.so` files' content to the `analyzer_binary_key` |
| Z3 refutation (`crosscheck-with-z3=true`) | the flag only | add the Z3 library version to the `analyzer_binary_key` |



Examples:

analyzer invocation:
/usr/bin/clang --analyze -Qunused-arguments -Xclang -analyzer-output=plist-multi-file -o /workspace/test-projects/tinyxml2/reports/xmltest.cpp_clangsa_3e85aaf332fe01343c3163ef26e631f7.plist -Xclang -analyzer-config -Xclang expand-macros=true -Xclang -analyzer-checker=core.BitwiseShift,core.CallAndMessage,core.DivideZero,core.NonNullParamChecker,core.NullDereference,core.StackAddressEscape,core.UndefinedBinaryOperatorResult,core.VLASize,core.uninitialized.ArraySubscript,core.uninitialized.Assign,core.uninitialized.Branch,core.uninitialized.CapturedBlockVariable,core.uninitialized.NewArraySize,core.uninitialized.UndefReturn,cplusplus.InnerPointer,cplusplus.Move,cplusplus.NewDelete,cplusplus.NewDeleteLeaks,cplusplus.PlacementNew,cplusplus.PureVirtualCall,cplusplus.StringChecker,deadcode.DeadStores,nullability.NullPassedToNonnull,nullability.NullReturnedFromNonnull,optin.cplusplus.UninitializedObject,optin.cplusplus.VirtualCall,optin.portability.UnixAPI,security.FloatLoopCounter,security.cert.env.InvalidPtr,security.insecureAPI.UncheckedReturn,security.insecureAPI.getpw,security.insecureAPI.gets,security.insecureAPI.mkstemp,security.insecureAPI.mktemp,security.insecureAPI.rand,security.insecureAPI.vfork,unix.API,unix.Malloc,unix.MallocSizeof,unix.MismatchedDeallocator,unix.StdCLibraryFunctions,unix.Vfork,unix.cstring.BadSizeArg,unix.cstring.NullArg,valist.CopyToSelf,valist.Uninitialized,valist.Unterminated -Xclang -analyzer-config -Xclang aggressive-binary-operation-simplification=true -x c++ -DTINYXML2_IMPORT -D_FILE_OFFSET_BITS=64 -I/workspace/test-projects/tinyxml2 -fvisibility=hidden -fvisibility-inlines-hidden --target=x86_64-linux-gnu -std=gnu++17 -idirafter /usr/include/c++/13 -idirafter /usr/include/x86_64-linux-gnu/c++/13 -idirafter /usr/include/c++/13/backward -idirafter /usr/local/include -idirafter /usr/include/x86_64-linux-gnu -idirafter /usr/include /workspace/test-projects/tinyxml2/xmltest.cpp


preprocessing:
Drop --analyze, the -Xclang -analyzer-* flags and the plist -o, then add -E. Everything that affects preprocessing stays: language, defines, include paths, target and standard. I also
  called clang directly instead of going through the /usr/lib/ccache wrapper, because ccache adds nothing for -E.

  clang -E \
    -x c++ \
    -DTINYXML2_IMPORT \
    -D_FILE_OFFSET_BITS=64 \
    -I/workspace/test-projects/tinyxml2 \
    -fvisibility=hidden -fvisibility-inlines-hidden \
    --target=x86_64-linux-gnu \
    -std=gnu++17 \
    -idirafter /usr/include/c++/13 \
    -idirafter /usr/include/x86_64-linux-gnu/c++/13 \
    -idirafter /usr/include/c++/13/backward \
    -idirafter /usr/local/include \
    -idirafter /usr/include/x86_64-linux-gnu \
    -idirafter /usr/include \
    /workspace/test-projects/tinyxml2/xmltest.cpp \
    -o /workspace/test-projects/tinyxml2/reports/xmltest.cpp.ii

  - The -fvisibility* flags don't change preprocessing. I kept them only so the command stays close to the original, and you can remove them.
  - To get output without # line markers, add -P. To keep comments as well, add -C.
  - To get the defined macros instead of the expanded source, use -E -dM (or -dD to get both).
  - To reproduce the analysis from the .ii file, run the original command but point it at xmltest.cpp.ii and change -x c++ to -x c++-cpp-output. This way the include and define flags are no
  longer needed.