# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
SQLAlchemy ORM model for the product configuration database.
"""
from datetime import datetime, timedelta
import sys

from sqlalchemy import Boolean, CHAR, Column, DateTime, Enum, ForeignKey, \
    Integer, MetaData, String, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import false, true

from ..permissions import get_permissions

CC_META = MetaData(naming_convention={
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

# Create base class for ORM classes.
Base = declarative_base(metadata=CC_META)


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, autoincrement=True, primary_key=True)
    endpoint = Column(String, nullable=False, unique=True)
    connection = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    run_limit = Column(Integer)
    report_limit = Column(Integer, nullable=False, server_default="500000")
    num_of_runs = Column(Integer, server_default="0")
    latest_storage_date = Column(DateTime, nullable=True)

    # Disable review status change on UI.
    is_review_status_change_disabled = Column(Boolean,
                                              server_default=false())

    confidentiality = Column(String, nullable=True)

    def __init__(self, endpoint, conn_str, name=None, description=None,
                 run_limit=None, report_limit=500000,
                 is_review_status_change_disabled=False,
                 confidentiality=None):
        self.endpoint = endpoint
        self.connection = conn_str
        self.display_name = name if name else endpoint
        self.description = description
        self.run_limit = run_limit
        self.report_limit = report_limit
        self.is_review_status_change_disabled = \
            bool(is_review_status_change_disabled)
        self.confidentiality = confidentiality


def __get_permission_names(scope=None):
    """
    Returns a list of strings which contains permission names.

    This function is used internally to set up the permission database.

    :param scope: One of the Permission class strings (e.g. 'SYSTEM'), which
      if given, filters the returned list of permissions to only definitions
      of the given scope.
    """

    return [perm.name for perm in get_permissions(scope)]


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


class PersonalAccessToken(Base):
    __tablename__ = 'personal_access_tokens'

    id = Column(Integer, autoincrement=True, primary_key=True)

    user_name = Column(String)

    token_name = Column(String)
    token = Column(CHAR(32), nullable=False, unique=True)

    description = Column(String)
    # List of group names separated by semicolons.
    groups = Column(String)

    last_access = Column(DateTime, nullable=False)
    expiration = Column(DateTime)

    auth_session_id = Column(
        Integer,
        ForeignKey('auth_sessions.id', deferrable=False, ondelete='SET NULL'),
        nullable=True)

    __table_args__ = (
        UniqueConstraint('user_name', 'token_name'),
    )

    def __init__(
        self,
        user_name,
        token_name,
        token,
        description,
        groups,
        auth_session_id
    ):
        self.user_name = user_name
        self.token_name = token_name
        self.token = token
        self.description = description
        self.groups = groups
        self.auth_session_id = auth_session_id
        self.last_access = datetime.now()
        self.expiration = self.last_access + timedelta(days=365)


class Configuration(Base):
    __tablename__ = 'server_configurations'

    id = Column(Integer, autoincrement=True, primary_key=True)
    config_key = Column(String,
                        nullable=False)

    config_value = Column(String)

    def __init__(self, config_key, config_value):
        self.config_key = config_key
        self.config_value = config_value


class OAuthSession(Base):
    __tablename__ = 'oauth_sessions'

    id = Column(Integer, autoincrement=True, primary_key=True)
    provider = Column(String, nullable=False)
    state = Column(String, nullable=False)
    code_verifier = Column(String, nullable=False)
    expires_at = Column(DateTime)

    def __init__(self, provider, state, code_verifier, expires_at):
        self.provider = provider
        self.state = state
        self.expires_at = expires_at
        self.code_verifier = code_verifier


class OAuthToken(Base):
    __tablename__ = 'oauth_tokens'

    id = Column(Integer, autoincrement=True, primary_key=True)
    access_token = Column(String, nullable=False)
    expires_at = Column(DateTime)
    refresh_token = Column(String, nullable=False)
    auth_session_id = Column(Integer,
                             ForeignKey('auth_sessions.id',
                                        deferrable=False,
                                        ondelete='CASCADE'),
                             nullable=False)

    def __init__(self, access_token, expires_at, refresh_token,
                 auth_session_id):
        self.access_token = access_token
        self.expires_at = expires_at
        self.refresh_token = refresh_token
        self.auth_session_id = auth_session_id


IDENTIFIER = {
    'identifier': "ConfigDatabase",
    'orm_meta': CC_META
}
