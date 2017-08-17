// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

include "shared.thrift"

namespace py ProductManagement
namespace js codeCheckerProductManagement


/*
struct PrivilegeRecord {
  1: string   name,
  2: bool     isGroup
}
typedef list<PrivilegeRecord> PrivilegeRecords
*/

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
  5: optional DatabaseConnection connection
}
typedef list<ProductConfiguration> ProductConfigurations

/* Product carries data to the end user's product list and tasks. */
struct Product {
  1: i64    id,
  2: string endpoint,
  3: string displayedName_b64,
  4: string description_b64,
  5: bool   connected,         // Indicates that the server could set up the database connection properly.
  6: bool   accessible         // Indicates whether the current user can access this product.
}
typedef list<Product> Products

service codeCheckerProductService {

  // Return the product management API version.
  string getAPIVersion(),

  // Returns the CodeChecker version that is running on the server.
  string getPackageVersion(),

  // *** Handling of product lists and metadata querying *** //

  // Get the list of product that matches the display name and endpoint
  // filters specified.
  Products getProducts(1: string productEndpointFilter,
                       2: string productNameFilter)
                       throws (1: shared.RequestFailed requestError),

  Product getCurrentProduct()
                            throws (1: shared.RequestFailed requestError),

  // *** Handling the add-modify-remove of registered products *** //

  ProductConfiguration getProductConfiguration(1: i64 productId)
                                               throws (1: shared.RequestFailed requestError),

  bool addProduct(1: ProductConfiguration product)
                  throws (1: shared.RequestFailed requestError),

  bool editProduct(1: i64 productId,
                   2: ProductConfiguration newConfiguration)
                   throws (1: shared.RequestFailed requestError),

  bool removeProduct(1: i64 productId)
                     throws (1: shared.RequestFailed requestError)

}
