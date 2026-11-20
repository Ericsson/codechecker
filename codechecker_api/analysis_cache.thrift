// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// Server-side analysis result cache. Product specific endpoint:
//   <server>/<product>/v<api version>/AnalysisCache
// Every call requires the PRODUCT_CACHE permission on the product.

include "shared.thrift"

namespace py codechecker_api.python.AnalysisCache_v6
namespace js codeCheckerAnalysisCache_v6

struct CacheContent {
  1: string filename,  // Role of the file in the cached result
                       // ("result.plist", "stdout.txt", "stderr.txt").
                       // Plain basename only, it must not be used as a
                       // file system path.
  2: string content,   // base64(zlib(file bytes))
}
typedef list<CacheContent> CacheContents

service AnalysisCache {

  // Store the given files for the given analysis key.
  // The key must be a sha256 hex digest (64 lowercase hex characters).
  // Throws RequestFailed if the files could not be stored.
  void writeCache(1: string        key,
                  2: CacheContents contents)
                  throws (1: shared.RequestFailed requestError),

  // Return the files stored for the given analysis key.
  // In case of a cache miss an empty list is returned.
  CacheContents readCache(1: string key)
                          throws (1: shared.RequestFailed requestError),
}
