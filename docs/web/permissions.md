Permission subsystem
====================

To configure access demarcation between multiple [products](products.md),
CodeChecker has it's permission system. Each user can be assigned some
permissions, and each action on the server requires a certain permission to be
present - otherwise the action will fail.

The username and group values that permissions can be delegated to are
retrieved via [user credentials](authentication.md). **For the permission
system to work, authentication must be enabled**, otherwise, the
unauthenticated guest user will only have the
[*default* permissions](permissions.md#default-value) given.

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
        * [`PRODUCT_VIEW`](#product-view)

# The master superuser (root) <a name="the-master-superuser"></a>

Each CodeChecker server at its first start generates a master superuser
(*root*) access credential which it prints into its standard output:

```sh
[WARNING] Server started without 'root.user' present in CONFIG_DIRECTORY!
A NEW superuser credential was generated for the server. This information IS
SAVED, thus subsequent server starts WILL use these credentials. You WILL NOT
get to see the credentials again, so MAKE SURE YOU REMEMBER THIS LOGIN!
-----------------------------------------------------------------
The superuser's username is 'AAAAAA' with the password 'aaaa0000'
-----------------------------------------------------------------
```

These credentials can be deleted and new ones can be requested by starting
CodeChecker server with the `--reset-root` flag. The credentials are always
**randomly generated**.

If the server has authentication enabled, the *root* user will **always have
access** despite of the configured authentication backends' decision, and
will automatically **have the `SUPERUSER` permission**.

# Managing permissions <a name="managing-permissions"></a>

![Global permission manager](images/permissions.png)

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

# Permission concepts <a name="permission-concepts"></a>

Each permission has a unique name, such as `SUPERUSER` or `PRODUCT_ADMIN`.

## Default value <a name="default-value"></a>

Permissions can either be *not granted* or *granted* by default.

If the server is running with authentication &ndash; all permissions are
*default not granted*, which means only the users (or LDAP groups) where the
permission is explicitly set will have various access rights.

If the server is running without authentication &ndash; in this case there are
no "users" as everyone is a guest &ndash; **every permission is automatically
granted**.

## Permission inheritance <a name="permission-inheritance"></a>

Certain permissions automatically imply other permissions, e.g. a
`PRODUCT_ADMIN` is automatically given every product-level permission.

Permissions achieved through inheritance are exempt from the *default*
behaviour mentioned above. If no user has the `PRODUCT_ACCESS` permission,
every user will have it (because it is a *default granted* permission), despite
an existing `PRODUCT_ADMIN` inheriting the permission.

## Permission manager <a name="permission-manager"></a>

Permissions have a clear "chain of command" set in CodeChecker. Only a user who
has permission `A`'s manager permission can grant or revoke other users' rights
to `A`.

# Available permissions <a name="available-permissions"></a>

> Developer guide: See the [API documentation](api/README.md) for the list of
> permissions and which API call requires which permission exactly.

## Server-wide (global) permissions <a name="global-permissions"></a>

### `SUPERUSER` <a name="superuser"></a>

|    Default    |
|---------------|
| *Not* granted |

The `SUPERUSER` permission is the highest possible permission available.

Superusers can **manage** and automatically **have every permission** in the
system.

> **`SUPERUSER` is a dangerous permission to grant**, as a superuser can
> immediately change everything on the server, from demoting other superusers
> to destroying analysis results!

## Product-level permissions <a name="product-level-permissions"></a>

### `PRODUCT_ADMIN` <a name="product-admin"></a>

|    Default    |
|---------------|
| *Not* granted |

The product administrator is responsible for the management of an individual
product. They can edit the product's appearance (displayed name and
description) and delegate other product-level permissions to other users.

Product administrators cannot change the *URL* or the *database configuration*
of the product.

Product admins are automatically given other `PRODUCT_` permissions.

### `PRODUCT_ACCESS` <a name="product-access"></a>

| Default |    Managed by   |          Inherited from          |
|---------|-----------------|----------------------------------|
| Granted | `PRODUCT_ADMIN` | `PRODUCT_ADMIN`, `PRODUCT_STORE` |


The basic permission to access analysis results stored in the product. With
this permission, the user can browse analysis results, comment, set review
status, etc.

### `PRODUCT_STORE` <a name="product-store"></a>

| Default |    Managed by   | Inherited from  |
|---------|-----------------|-----------------|
| Granted | `PRODUCT_ADMIN` | `PRODUCT_ADMIN` |

Users need the `PRODUCT_STORE` permission to `store` analysis runs and to
delete existing analysis runs from the server.

### `PRODUCT_VIEW` <a name="product-view"></a>

| Default |    Managed by   | Inherited from  |
|---------|-----------------|-----------------|
| Granted | `PRODUCT_ADMIN` | `PRODUCT_ADMIN`, `PRODUCT_STORE`, `PRODUCT_ACCESS` |

Users need the `PRODUCT_VIEW` permission to `view` analysis runs without modifying any properties of the runs. 