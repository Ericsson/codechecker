# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module defines the list of permissions of a CodeChecker server, and
provides the handling of permission matching and databases.
"""


from abc import ABCMeta
from abc import abstractmethod

from sqlalchemy import and_, func

from codechecker_api_shared.ttypes import Permission as PermissionEnum

from codechecker_common.logger import get_logger

LOG = get_logger('server')
config_db_model = None  # Module will be loaded later...


class Permission(metaclass=ABCMeta):
    """
    The base class for a permission declaration.
    """

    def __init__(self, name, default_enable=True,
                 inherited_from=None, managed_by=None, manages_self=False):
        """
        Creates the definition of a new permission.

        :param name:           The name of the permission
        :param default_enable: If False, only the people explicitly given this
          permission are marked as having it. If True, an empty list of people
          given the permission means that everyone has the permission, if the
          server is running in authentication ENABLED mode.
        :param inherited_from: The list of permissions which automatically
          imply this permission. (Disjunctive list, i.e. if the user has
          either of these permissions specified, they have the current one
          too.)
          Permissions can only be inherited from another permission in the
          same, or a broader scope.
        :param managed_by:     The list of permissions from which the user must
          have at least one to manage other users' authorisation on this
          permission.
          Permissions can only be managed by having permissions in the same,
          or a broader scope.
        :param manages_self:   If True, people who have this permission also
          can manage this permission.
        """
        self.name = name
        self.default_enable = default_enable

        if inherited_from is None:
            inherited_from = []
        if managed_by is None:
            managed_by = []

        # Permission can be managed by itself.
        if manages_self:
            managed_by = [self] + managed_by

        # The SUPERUSER permission is a hardcoded special case.
        if name == 'SUPERUSER':
            # SUPERUSER is the maximum rank, it cannot be inherited.
            self.inherited_from = []
        else:
            # Granting SUPERUSER automatically grants every other permission.
            if SUPERUSER not in inherited_from:
                inherited_from = [SUPERUSER] + inherited_from

            # SUPERUSERs can manage every permission by default.
            if SUPERUSER not in managed_by:
                managed_by = [SUPERUSER] + managed_by

            self.inherited_from = inherited_from

        self.managed_by = managed_by

    # Contains the list of arguments required by __call__ to initialise a
    # permission handler.
    # (Unfortunately, inspect.getargspec() doesn't seem to work when
    # called from the API handler.)
    CALL_ARGS = []

    @abstractmethod
    def __call__(self, *args, **kwargs):
        """
        Instantiate a PermissionHandler class for the current permission.
        This instantiated object can be used to query and manage permissions.

        This method is overridden in subclasses so that permissions of
        different scopes can create an appropriate handler.

        The amount of arguments for this function may vary, depending on the
        scope of the permission.
        """
        pass


class PermissionHandler(metaclass=ABCMeta):
    """
    The abstract base class for an object that interfaces with the permission
    database to query and manage permissions.
    """

    def __init__(self, permission):
        """
        Create the Permission Handler.

        :param permission:  The Permission object that instantiated this
          handler.
        """
        self._permission = permission
        self._perm_name = permission.name

        # The actual database managing methods (beginning with __) need the
        # database model to be available, but we cannot say
        # "import config_db_model" at the top of this file because the database
        # module needs this module to be fully loaded (permissions constants
        # defined) to set up the schema.
        #
        # Thus, a deferred loading is used here, the first time a permission
        # handler is initialized. Most likely this import does nothing,
        # as the server already executed loading the config_db_model,
        # so we just set the name to properly point to the module object.
        global config_db_model
        if config_db_model is None:
            LOG.debug("Handler initiated for first time, loading ORM...")
            from .database import config_db_model as ConfigDB
            config_db_model = ConfigDB

    # These high-level methods are used by client code. These contain
    # control flow that are shared for every permission handler
    # (such as handling default_enabled), but these don't access any
    # database backend.
    def add_permission(self, auth_name, is_group=False, user_name='Anonymous'):
        """
        Registers the current permission for the given authentication
        identifier, which is either a username, or a group name, depending on
        is_group.
        """
        if auth_name == "*":
            raise ValueError("'*' is a special token which can NOT be "
                             "directly added to the permission table.")

        added = self._add_perm_impl(auth_name, is_group)

        if added:
            LOG.info("Permission '%s' added for %s '%s' by '%s'.",
                     self._perm_name, 'group' if is_group else 'user',
                     auth_name, user_name)

            # Set the invariant for default_enable.
            if self._permission.default_enable:
                users, groups = self.list_permitted()

                # If a user was added (and this is the first add to a default
                # enabled permission) the table must contain '*' and the user,
                # otherwise a '*' and the currently added group.
                if (not is_group and len(users) == 2 and not groups) or \
                        (is_group and len(users) == 1 and len(groups) == 1):
                    self._rem_perm_impl("*", False)
        else:
            LOG.info("Permission '%s' already added for %s '%s'!",
                     self._perm_name, 'group' if is_group else 'user',
                     auth_name)

    def remove_permission(self, auth_name, is_group=False,
                          user_name='Anonymous'):
        """
        Removes the current permission from the given authentication
        identifier.
        """
        if auth_name == "*":
            raise ValueError("'*' is a special token which can NOT be "
                             "directly removed from the permission table.")

        removed = self._rem_perm_impl(auth_name, is_group)

        if removed:
            LOG.info("Permission '%s' removed from %s '%s' by '%s'.",
                     self._perm_name, 'group' if is_group else 'user',
                     auth_name, user_name)

            # Set the invariant for default_enable.
            if self._permission.default_enable:
                users, groups = self.list_permitted()
                if not users and not groups:
                    self._add_perm_impl("*", False)
        else:
            LOG.info("Permission '%s' already removed from %s '%s'!",
                     self._perm_name, 'group' if is_group else 'user',
                     auth_name)

    def has_permission(self, auth_session):
        """
        Returns whether or not the given authenticated user session
        (or None, if authentication is disabled on the server!) is given
        the current permission.
        """
        if not auth_session:
            # If the user does not have an auth_session it means it is a guest
            # and the server is running in authentication disabled mode.
            # All permissions are automatically granted in this case.
            return True
        elif auth_session.is_root and self._perm_name == 'SUPERUSER':
            # The special master superuser (root) automatically has the
            # SUPERUSER permission.
            return True

        name = self._has_perm_impl([auth_session.user], False)
        groups = self._has_perm_impl(auth_session.groups, True)

        if not name and not groups and self._permission.default_enable:
            # Default enabled permission work in a way that if no one has the
            # permission, everyone has it.
            # ("No-one has the permission" is represented as a * user having
            # the permission, this invariant kept up by add() and remove().)
            return self._has_perm_impl(["*"], False)

        return name or groups

    def list_permitted(self):
        """
        Returns a pair of usernames and groups that are given the current
        permission.
        """
        records = self._list_authorised_impl()
        users = []
        groups = []
        for name, is_group in records:
            if is_group:
                groups.append(name)
            else:
                users.append(name)

        return users, groups

    # These abstract methods are overridden in the subclasses to interface
    # with some database backend in a particular way, depending on the
    # permission's scope.
    @abstractmethod
    def _add_perm_impl(self, auth_name, is_group=False):
        pass

    @abstractmethod
    def _rem_perm_impl(self, auth_name, is_group=False):
        pass

    @abstractmethod
    def _has_perm_impl(self, auth_names, are_groups=False):
        pass

    @abstractmethod
    def _list_authorised_impl(self):
        pass


class SystemPermission(Permission):
    """
    Represents a permission which scope is the entire configuration database,
    essentially the full server.
    """

    class Handler(PermissionHandler):
        """
        This class is used to query server-wide permissions.
        """

        def __init__(self, permission, config_db_session):
            """
            Create a new system-wide permission handler.

            :param permission:        The Permission object that instantiated
              this handler.
            :param config_db_session: A database session that refers to the
              configuration database of the server.
            """
            super(SystemPermission.Handler, self).__init__(permission)
            self.__session = config_db_session

        def __get_perm_record(self, auth_name, is_group):
            SysPerm = config_db_model.SystemPermission

            record = self.__session. \
                query(SysPerm). \
                filter(and_(
                    SysPerm.permission == self._perm_name,
                    func.lower(SysPerm.name) == auth_name.lower(),
                    SysPerm.is_group == is_group
                )).one_or_none()

            return record

        def __get_stored_auth_name_and_permissions(self, auth_name, is_group):
            """
            Query user or group system permission set.

            :param auth_name:   User's name or name of group name case
                                insensitive pattern.
            :param is_group:    Determines that the previous name either a
                                user's name or a group name.
            :returns:           A touple in (name, permission_set) structure.
            """

            SysPerm = config_db_model.SystemPermission

            stored_auth_name = auth_name
            permissions = set()
            for name, permission in self.__session.query(
                    SysPerm.name, SysPerm.permission).filter(and_(
                    func.lower(SysPerm.name) == auth_name.lower(),
                    SysPerm.is_group == is_group)):
                stored_auth_name = name
                permissions.add(permission)

            return (stored_auth_name, permissions)

        def _add_perm_impl(self, auth_name, is_group=False):
            if not auth_name:
                return False

            stored_auth_name, permissions = \
                self.__get_stored_auth_name_and_permissions(
                    auth_name, is_group)

            if not permissions:  # This account have not got permission yet.
                new_permission_record = config_db_model.SystemPermission(
                    self._permission.name, auth_name, is_group)
            else:  # There are at least one permission of the user.
                if self._permission.name in permissions:
                    return False  # Required permission already granted

                new_permission_record = config_db_model.SystemPermission(
                    self._permission.name, stored_auth_name, is_group)

            self.__session.add(new_permission_record)
            return True

        def _rem_perm_impl(self, auth_name, is_group=False):
            if not auth_name:
                return False

            perm_record = self.__get_perm_record(auth_name, is_group)
            if perm_record:
                self.__session.delete(perm_record)
                return True

        def _has_perm_impl(self, auth_names, are_groups=False):
            if not auth_names:
                return False

            auth_names_lower = [name.lower() for name in auth_names]
            SysPerm = config_db_model.SystemPermission
            query = self.__session. \
                query(SysPerm). \
                filter(and_(
                    SysPerm.permission == self._perm_name,
                    func.lower(SysPerm.name).in_(auth_names_lower),
                    SysPerm.is_group == are_groups
                ))

            exists = self.__session.query(query.exists()).scalar()
            return exists

        def _list_authorised_impl(self):
            SysPerm = config_db_model.SystemPermission

            result = self.__session. \
                query(SysPerm). \
                filter(SysPerm.permission == self._perm_name).all()

            return [(p.name, p.is_group) for p in result]

    def __init__(self, name, **kwargs):
        super(SystemPermission, self).__init__(name, **kwargs)

    CALL_ARGS = ['config_db_session']

    def __call__(self, config_db_session):
        """
        Create the permission handler for this system-wide permission,
        for the given configuration database session.
        """

        return SystemPermission.Handler(self, config_db_session)


class ProductPermission(Permission):
    """
    Represents a permission which scope is a particular product.
    """

    class Handler(PermissionHandler):
        """
        This class is used to query product-wide permissions.
        """

        def __init__(self, permission, config_db_session, product_id):
            """
            Create a new product-wide permission handler.

            :param permission:        The Permission object that instantiated
              this handler.
            :param config_db_session: A database session that refers to the
              configuration database of the server.
            :param product_id:        The ID of the product for which the
              permission is instantiated.
            """
            super(ProductPermission.Handler, self).__init__(permission)
            self.__session = config_db_session
            self.__product_id = product_id

        def __get_perm_record(self, auth_name, is_group):
            ProdPerm = config_db_model.ProductPermission

            record = self.__session. \
                query(ProdPerm). \
                filter(and_(
                    ProdPerm.permission == self._perm_name,
                    ProdPerm.product_id == self.__product_id,
                    func.lower(ProdPerm.name) == auth_name.lower(),
                    ProdPerm.is_group == is_group
                )).one_or_none()

            return record

        def __get_stored_auth_name_and_permissions(self, auth_name, is_group):
            """
            Query user or group product permission set.

            :param auth_name:   User's name or name of group name case
                                insensitive pattern.
            :param is_group:    Determines that the previous name either a
                                user's name or a group name.
            :returns:           A touple in (name, permission_set) structure.
            """
            ProdPerm = config_db_model.ProductPermission

            stored_auth_name = auth_name
            permissions = set()
            for name, permission in self.__session.query(
                    ProdPerm.name, ProdPerm.permission).filter(and_(
                    ProdPerm.product_id == self.__product_id,
                    func.lower(ProdPerm.name) == auth_name.lower(),
                    ProdPerm.is_group == is_group)):
                stored_auth_name = name
                permissions.add(permission)

            return (stored_auth_name, permissions)

        def _add_perm_impl(self, auth_name, is_group=False):
            if not auth_name:
                return False

            stored_auth_name, permission_set = \
                self.__get_stored_auth_name_and_permissions(
                    auth_name, is_group)

            if not permission_set:  # This account have not got permission yet.
                new_permission_record = config_db_model.ProductPermission(
                    self._permission.name, self.__product_id, auth_name,
                    is_group)
            else:  # There are at least one permission of the user.
                if self._permission.name in permission_set:
                    return False  # Required permission already granted

                new_permission_record = config_db_model.ProductPermission(
                    self._permission.name, self.__product_id,
                    stored_auth_name, is_group)

            self.__session.add(new_permission_record)
            return True

        def _rem_perm_impl(self, auth_name, is_group=False):
            if not auth_name:
                return False

            perm_record = self.__get_perm_record(auth_name, is_group)
            if perm_record:
                self.__session.delete(perm_record)
                return True

        def _has_perm_impl(self, auth_names, are_groups=False):
            if not auth_names:
                return False

            # Compare authorization names in a case insensitive way.
            auth_names_lower = [name.lower() for name in auth_names]
            ProdPerm = config_db_model.ProductPermission
            query = self.__session. \
                query(ProdPerm). \
                filter(and_(
                    ProdPerm.permission == self._perm_name,
                    ProdPerm.product_id == self.__product_id,
                    func.lower(ProdPerm.name).in_(auth_names_lower),
                    ProdPerm.is_group.is_(are_groups)
                ))

            exists = self.__session.query(query.exists()).scalar()
            return exists

        def _list_authorised_impl(self):
            ProdPerm = config_db_model.ProductPermission

            result = self.__session. \
                query(ProdPerm). \
                filter(and_(
                    ProdPerm.permission == self._perm_name,
                    ProdPerm.product_id == self.__product_id
                )).all()

            return [(p.name, p.is_group) for p in result]

    def __init__(self, name, **kwargs):
        super(ProductPermission, self).__init__(name, **kwargs)

    CALL_ARGS = ['config_db_session', 'productID']

    def __call__(self, config_db_session, productID):
        """
        Create the permission handler for this product-wide permission
        on a particular product, managed through the given configuration
        database session.
        """

        return ProductPermission.Handler(self, config_db_session, productID)

# ---------------------------------------------------------------------------


PERMISSION_SCOPES = {
    'SYSTEM': SystemPermission,
    'PRODUCT': ProductPermission
}

__PERM_TO_API = {}
__API_TO_PERM = {}


def _create_permission(clazz, name, **kwargs):
    """
    Create a new permission and register it.

    :param clazz:  The subclass of Permission which will be instantiated.
    :param name:   The name of the permission. This is corresponding to the
      enum value over the API, usually in full capitals.
    :param kwargs: The rest of the argument dict will be passed as-is to the
      constructor of clazz.
    :return: The created permission instance.
    """

    permission = clazz(name, **kwargs)
    enum_value = PermissionEnum._NAMES_TO_VALUES[name]

    __PERM_TO_API[permission] = enum_value
    __API_TO_PERM[enum_value] = permission

    return permission


def get_permissions(scope=None):
    """
    Returns a list of permissions.

    :param scope: One of the Permission class strings (e.g. 'SYSTEM'), which
      if given, filters the returned list of permissions to only definitions
      of the given scope.
    """

    if scope is not None and scope not in PERMISSION_SCOPES:
        return []

    ret = []
    for _, perm in sorted(__API_TO_PERM.items()):
        if scope is not None and \
                not isinstance(perm, PERMISSION_SCOPES[scope]):
            continue
        ret.append(perm)
    return ret


def permission_from_api_enum(key):
    """
    Returns the Permission object for the associated API enum value.
    """
    return __API_TO_PERM[key]


def api_enum_for_permission(permission):
    """
    Return the API enum value for the given permission object.
    """
    return __PERM_TO_API[permission]


def handler_from_scope_params(permission, extra_params):
    """
    Construct the given permission's handler using the scope-specific extra
    arguments (received from the API). This method filters the extra_params
    to the values actually needed by the handler constructor.
    """

    # Filter the list of arguments of the handler factory __call__()
    # with the arguments given by the API.
    args_to_pass = set(extra_params).intersection(permission.CALL_ARGS)

    kwargs = {key: extra_params[key] for key in args_to_pass}
    return permission(**kwargs)


def initialise_defaults(scope, extra_params):
    """
    Helper function which creates the default-permission records in the
    database for a given scope and for the scope-specific extra params.

    This is usually used at server start (for SYSTEM permissions) and the
    creation of a new product (for PRODUCT permissions), etc.
    """

    perms = [perm for perm in get_permissions(scope)]

    for perm in perms:
        handler = handler_from_scope_params(perm, extra_params)
        users, groups = handler.list_permitted()

        if perm.default_enable and not users and not groups:
            # Calling the implementation method directly as this call is
            # needed to set an invariant which the interface method would
            # presume to be already standing.
            handler._add_perm_impl('*', False)
        elif not perm.default_enable and '*' in users:
            # If a permission changed meanwhile (this should NOT be a usual
            # case!), do not let the '*' be locked into the database forever.
            handler._rem_perm_impl('*', False)


def require_permission(permission, extra_params, user):
    """
    Returns whether or not the given user has the given permission.

    :param extra_params: The scope-specific argument dict, which already
      contains a valid database session.
    """

    handler = handler_from_scope_params(permission,
                                        extra_params)
    if handler.has_permission(user):
        return True

    # If the user for some reason does not have the permission directly
    # (or by default), we need to walk the inheritance chain of the permission.
    ancestors = permission.inherited_from
    while ancestors:
        handler = handler_from_scope_params(ancestors[0], extra_params)

        if handler.has_permission(user):
            return True
        else:
            ancestors = ancestors[1:] + ancestors[0].inherited_from

    return False


def require_manager(permission, extra_params, user):
    """
    Returns whether or not the given user has rights to manage the given
    permission.

    :param extra_params: The scope-specific argument dict, which already
      contains a valid database session.
    """

    for manager in permission.managed_by:
        manager_handler = handler_from_scope_params(manager,
                                                    extra_params)
        if manager_handler.has_permission(user):
            return True

    return False

# ---------------------------------------------------------------------------
# Define the permissions available.
# Please refer to the user guide and the API documentation on which actions
# require which permission in particular.

# -- System-level permissions --


SUPERUSER = _create_permission(SystemPermission, 'SUPERUSER',
                               default_enable=False,
                               manages_self=True)

PERMISSION_VIEW = _create_permission(
    SystemPermission, 'PERMISSION_VIEW',
    default_enable=False,
    managed_by=[SUPERUSER])

# -- Product-level permissions --

PRODUCT_ADMIN = _create_permission(ProductPermission, 'PRODUCT_ADMIN',
                                   default_enable=False,
                                   managed_by=[SUPERUSER],
                                   manages_self=True)

PRODUCT_STORE = _create_permission(ProductPermission, 'PRODUCT_STORE',
                                   default_enable=False,
                                   inherited_from=[PRODUCT_ADMIN],
                                   managed_by=[PRODUCT_ADMIN])

PRODUCT_ACCESS = _create_permission(ProductPermission, 'PRODUCT_ACCESS',
                                    default_enable=False,
                                    inherited_from=[PRODUCT_ADMIN,
                                                    PRODUCT_STORE],
                                    managed_by=[PRODUCT_ADMIN])

PRODUCT_VIEW = _create_permission(ProductPermission, 'PRODUCT_VIEW',
                                  default_enable=False,
                                  inherited_from=[PRODUCT_ACCESS,
                                                  PRODUCT_ADMIN,
                                                  PRODUCT_STORE],
                                  managed_by=[PRODUCT_ADMIN])
