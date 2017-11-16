Permission subsystem
====================

To configure access demarcation between multiple [products](/docs/products.md),
CodeChecker has it's permission system. Each user can be assigned some
permissions, and each action on the server requires a certain permission to be
present - otherwise the action will fail.

The username and group values that permissions can be delegated to are
retrieved via [user credentials](/docs/authentication.md). **For the permission
system to work, authentication must be enabled**, otherwise, the
unauthenticated guest user will only have the
[*default* permissions](/docs/permissions.md#default-value) given.

Different *scopes* of CodeChecker use different permissions. Currently,
permissions can be defined on the server level (system/global permission), or
on the product level.

Table of Contents
=================
* [The master superuser (root)](#the-master-superuser)
* [Managing permissions](#managing-permissions)
* [Permission concepts](#permission-concepts)
  * [Default value](#default-value)
  * [Permission inheritance](#permission-inheritance)
  * [Permission manager](#permission-manager)
* [Available permissions](#available-permissions)
  * [Server-wide (global) permissions](#global-permissions)
    * [`SUPERUSER`](#superuser)
  * [Product-level permissions](#product-level-permissions)
    * [`PRODUCT_ADMIN`](#product-admin)
    * [`PRODUCT_ACCESS`](#product-access)
    * [`PRODUCT_STORE`](#product-store)

## <a name="the-master-superuser"></a> The master superuser (root)

Each CodeChecker server at its first start generates a master superuser
(*root*) access credential which it prints into its standard output:

~~~~~~~~~~~~~~~~~~~~~
[WARNING] Server started without 'root.user' present in CONFIG_DIRECTORY!
A NEW superuser credential was generated for the server. This information IS
SAVED, thus subsequent server starts WILL use these credentials. You WILL NOT
get to see the credentials again, so MAKE SURE YOU REMEMBER THIS LOGIN!
-----------------------------------------------------------------
The superuser's username is 'AAAAAA' with the password 'aaaa0000'
-----------------------------------------------------------------
~~~~~~~~~~~~~~~~~~~~~

These credentials can be deleted and new ones can be requested by starting
CodeChecker server with the `--reset-root` flag. The credentials are always
**randomly generated**.

If the server has authentication enabled, the *root* user will **always have
access** despite of the configured authentication backends' decision, and
will automatically **have the `SUPERUSER` permission**.

## <a name="managing-permissions"></a> Managing permissions

![Global permission manager](/docs/images/permissions.png)

 * Server-wide permissions can be edited by clicking *Edit global permissions*.
 * Product-level permissions can be edited by clicking the edit icon for the
   product you want to configure the permissions for.

Permissions can be managed on the web interface. From the drop-down, select the
permission you want to configure. The two lists show the users and groups
known to the system - if a tick is present in its row, the given user or group
has the permission directly granted. (Users who only have a certain permission
through permission inheritance are not shown with a tick.)

Only the permissions you have rights to manage are shown in the drop-down.

You can edit multiple permissions opening the window only once. Simply tick or
un-tick the users/groups you want to give the permission to or revoke from them.
Clicking *OK* will save the changes to the database.

## <a name="permission-concepts"></a> Permission concepts

Each permission has a unique name, such as `SUPERUSER` or `PRODUCT_ADMIN`.

### <a name="default-value"></a> Default value

Permissions can either be *not granted* or *granted* by default.

Some permissions are *default not granted*, which means that only users whom
are explicitly given the permission have it.

Some permissions are *default granted*, which means that initially, every user
has the permission. However, if at least one user or group is explicitly
given the permission, only the users who have the permission given will be
able to utilise it.

If the server is running without authentication &ndash; in this case there are
no "users" as everyone is a guest &ndash; **every permission is automatically
granted**.

### <a name="permission-inheritance"></a> Permission inheritance

Certain permissions automatically imply other permissions, e.g. a
`PRODUCT_ADMIN` is automatically given every product-level permission.

Permissions achieved through inheritance are exempt from the *default*
behaviour mentioned above. If no user has the `PRODUCT_ACCESS` permission,
every user will have it (because it is a *default granted* permission), despite
an existing `PRODUCT_ADMIN` inheriting the permission.

### <a name="permission-manager"></a> Permission manager

Permissions have a clear "chain of command" set in CodeChecker. Only a user who
has permission `A`'s manager permission can grant or revoke other users' rights
to `A`.

## <a name="available-permissions"></a> Available permissions

> Developer guide: See the [API documentation](/api/README.md) for the list of
> permissions and which API call requires which permission exactly.

### <a name="global-permissions"></a> Server-wide (global) permissions

#### <a name="superuser"></a> `SUPERUSER`

|    Default    |
|---------------|
| *Not* granted |

The `SUPERUSER` permission is the highest possible permission available.

Superusers can **manage** and automatically **have every permission** in the
system.

> **`SUPERUSER` is a dangerous permission to grant**, as a superuser can
> immediately change everything on the server, from demoting other superusers
> to destroying analysis results!

### <a name="product-level-permissions"></a> Product-level permissions

#### <a name="product-admin"></a> `PRODUCT_ADMIN`

|    Default    |
|---------------|
| *Not* granted |

The product administrator is responsible for the management of an individual
product. They can edit the product's appearance (displayed name and
description) and delegate other product-level permissions to other users.

Product administrators cannot change the *URL* or the *database configuration*
of the product.

Product admins are automatically given other `PRODUCT_` permissions.

#### <a name="product-access"></a> `PRODUCT_ACCESS`

| Default |    Managed by   |          Inherited from          |
|---------|-----------------|----------------------------------|
| Granted | `PRODUCT_ADMIN` | `PRODUCT_ADMIN`, `PRODUCT_STORE` |


The basic permission to access analysis results stored in the product. With
this permission, the user can browse analysis results, comment, set detection
status, etc.

#### <a name="product-store"></a> `PRODUCT_STORE`

| Default |    Managed by   | Inherited from  |
|---------|-----------------|-----------------|
| Granted | `PRODUCT_ADMIN` | `PRODUCT_ADMIN` |

Users need the `PRODUCT_STORE` permission to `store` analysis runs and to
delete existing analysis runs from the server.
