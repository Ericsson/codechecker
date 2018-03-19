# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
SQLAlchemy ORM model for the product configuration database.
"""

from __future__ import print_function
from __future__ import unicode_literals
from datetime import datetime
import sys

from sqlalchemy import MetaData, Column, Integer, Enum, String, Boolean, \
    ForeignKey, CHAR, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import true

from libcodechecker.server import permissions

CC_META = MetaData(naming_convention={
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

# Create base class for ORM classes.
Base = declarative_base(metadata=CC_META)


class DBVersion(Base):
    __tablename__ = 'db_version'
    # TODO: constraint, only one line in this table!
    major = Column(Integer, primary_key=True)
    minor = Column(Integer, primary_key=True)

    def __init__(self, major, minor):
        self.major = major
        self.minor = minor


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, autoincrement=True, primary_key=True)
    endpoint = Column(String, nullable=False, unique=True)
    connection = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    run_limit = Column(Integer)

    def __init__(self, endpoint, conn_str, name=None, description=None,
                 run_limit=None):
        self.endpoint = endpoint
        self.connection = conn_str
        self.display_name = name if name else endpoint
        self.description = description
        self.run_limit = run_limit


def __get_permission_names(scope=None):
    """
    Returns a list of strings which contains permission names.

    This function is used internally to set up the permission database.

    :param scope: One of the Permission class strings (e.g. 'SYSTEM'), which
      if given, filters the returned list of permissions to only definitions
      of the given scope.
    """

    return [perm.name for perm in permissions.get_permissions(scope)]


class SystemPermission(Base):
    __tablename__ = 'permissions_system'

    id = Column(Integer, autoincrement=True, primary_key=True)
    permission = Column(Enum(
        *sys.modules[__name__].__dict__['__get_permission_names']('SYSTEM'),
        name='sys_perms'))
    name = Column(String, nullable=False)
    is_group = Column(Boolean, nullable=False)

    def __init__(self, permission, name, is_group=False):
        self.permission = permission
        self.name = name
        self.is_group = is_group


class ProductPermission(Base):
    __tablename__ = 'permissions_product'

    id = Column(Integer, autoincrement=True, primary_key=True)
    permission = Column(Enum(
        *sys.modules[__name__].__dict__['__get_permission_names']('PRODUCT'),
        name='product_perms'))
    product_id = Column(Integer, ForeignKey('products.id',
                                            deferrable=False,
                                            initially='IMMEDIATE',
                                            ondelete='CASCADE'),
                        nullable=False)
    name = Column(String, nullable=False)
    is_group = Column(Boolean, nullable=False)

    def __init__(self, permission, product_id, name, is_group=False):
        self.permission = permission
        self.product_id = product_id
        self.name = name
        self.is_group = is_group


class Session(Base):
    __tablename__ = 'auth_sessions'

    id = Column(Integer, autoincrement=True, primary_key=True)

    user_name = Column(String)
    token = Column(CHAR(32), nullable=False, unique=True)

    # List of group names separated by semicolons.
    groups = Column(String)

    last_access = Column(DateTime, nullable=False)

    # Token description.
    description = Column(String)

    can_expire = Column(Boolean, server_default=true(), default=True)

    def __init__(self, token, user_name, groups, description=None,
                 can_expire=True):
        self.token = token
        self.user_name = user_name
        self.groups = groups
        self.description = description
        self.can_expire = can_expire
        self.last_access = datetime.now()


IDENTIFIER = {
    'identifier': "ConfigDatabase",
    'orm_meta': CC_META,
    'version_class': DBVersion
}
