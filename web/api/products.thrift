// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

include "codechecker_api_shared.thrift"

namespace py ProductManagement_v6
namespace js codeCheckerProductManagement_v6


struct DatabaseConnection {
  1:          string engine,         // The database engine, such as "sqlite" or "postgresql".
  2:          string host,
  3:          i32    port,
  4:          string username_b64,
  5: optional string password_b64,   // Database password is NOT sent server->client!
  6:          string database        // SQLite: Database file path; PostgreSQL: Database name
}

/* ProductConfiguration carries administrative data regarding product settings. */
struct ProductConfiguration {
  1:          i64                id,
  2:          string             endpoint,
  3:          string             displayedName_b64,
  4:          string             description_b64,
  5: optional DatabaseConnection connection,
  6:          i64                runLimit,
  7: optional bool               isReviewStatusChangeDisabled,
}
typedef list<ProductConfiguration> ProductConfigurations

/* Product carries data to the end user's product list and tasks. */
struct Product {
  1: i64               id,
  2: string            endpoint,
  3: string            displayedName_b64,
  4: string            description_b64,
  5: bool              connected,                       // True only if database status is OK.
                                                        // !DEPRECATED FLAG databaseStatus is used to get the status of the database.
  6: bool              accessible,                      // Indicates whether the current user can access this product.
  7: bool              administrating,                  // Indicates that the current user can administrate the product.
  8: codechecker_api_shared.DBStatus   databaseStatus,  // Indicates the database backend status.
  9: i64               runCount,                        // Number of runs in the product.
  10: string           latestStoreToProduct,            // Latest date from the runs when the run in the product was updated.
  11: i64              runLimit,                        // Number of allowed runs for this product.
  12: list<string>     admins,                          // Administrators of this product.
  13: list<string>     runStoreInProgress,              // List of run names which are in progress.
}
typedef list<Product> Products

service codeCheckerProductService {

  // Returns the CodeChecker version that is running on the server.
  // !DEPRECATED Use ServerInfo API to get the package version.
  string getPackageVersion(),

  // *** Handling of product lists and metadata querying *** //

  // Returns true if the current user is a PRODUCT_ADMIN of any product
  // on the server.
  bool isAdministratorOfAnyProduct()
                                   throws (1: codechecker_api_shared.RequestFailed requestError),

  // Get the list of product that matches the display name and endpoint
  // filters specified.
  Products getProducts(1: string productEndpointFilter,
                       2: string productNameFilter)
                       throws (1: codechecker_api_shared.RequestFailed requestError),

  Product getCurrentProduct()
                            throws (1: codechecker_api_shared.RequestFailed requestError),

  // *** Handling the add-modify-remove of registered products *** //

  ProductConfiguration getProductConfiguration(1: i64 productId)
                                               throws (1: codechecker_api_shared.RequestFailed requestError),

  // PERMISSION: SUPERUSER
  bool addProduct(1: ProductConfiguration product)
                  throws (1: codechecker_api_shared.RequestFailed requestError),

  // PERMISSION: PRODUCT_ADMIN (for basic metadata editing),
  //             SUPERUSER     (for connection configuration editing)
  bool editProduct(1: i64 productId,
                   2: ProductConfiguration newConfiguration)
                   throws (1: codechecker_api_shared.RequestFailed requestError),

  // PERMISSION: SUPERUSER
  bool removeProduct(1: i64 productId)
                     throws (1: codechecker_api_shared.RequestFailed requestError)

}
