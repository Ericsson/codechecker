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
from datetime import datetime, timedelta, timezone
import sys
from typing import Optional

from sqlalchemy import Boolean, CHAR, Column, DateTime, Enum, ForeignKey, \
    Integer, MetaData, String, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import false

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

    def __init__(self, token, user_name, groups, description=None):
        self.token = token
        self.user_name = user_name
        self.groups = groups
        self.description = description
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
        expiration
    ):
        self.user_name = user_name
        self.token_name = token_name
        self.token = token
        self.description = description
        self.groups = groups
        self.last_access = datetime.now()
        self.expiration = self.last_access + timedelta(days=expiration)


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


class BackgroundTask(Base):
    """
    Information about background tasks executed on a CodeChecker service,
    potentially as part of a cluster, stored in the database.
    These entities store the metadata for the task objects, but no information
    about the actual "input" of the task exists in the database!
    """
    __tablename__ = "background_tasks"

    _token_length = 64

    machine_id = Column(String, index=True)
    """
    A unique, implementation-specific identifier of the actual CodeChecker
    server instance that knows how to execute the task.
    """

    token = Column(CHAR(length=_token_length), primary_key=True)
    kind = Column(String, nullable=False, index=True)
    status = Column(Enum(
        # A job token (and thus a BackgroundTask record) was allocated, but
        # the job is still under preparation.
        "allocated",

        # The job is pending on the server, but the server has all the data
        # available to eventually perform the job.
        "enqueued",

        # The server is actually performing the job.
        "running",

        # The server successfully finished completing the job.
        "completed",

        # The execution of the job failed.
        # In this stage, the "comments" field likely contains more information
        # that is not machine-readable.
        "failed",

        # The job never started, or its execution was terminated at the
        # request of the administrators.
        "cancelled",

        # The job never started, or its execution was terminated due to a
        # system-level reason (such as the server's foced shutdown).
        "dropped",
        ),
                    nullable=False,
                    default="enqueued",
                    index=True)

    product_id = Column(Integer,
                        ForeignKey("products.id",
                                   deferrable=False,
                                   initially="IMMEDIATE",
                                   ondelete="CASCADE"),
                        nullable=True,
                        index=True)
    """
    If the job is tightly associated with a product, the ID of the `Product`
    entity with which it is associated.
    """

    username = Column(String, nullable=True)
    """
    The main actor who was responsible for the creation of the job task.
    """

    summary = Column(String, nullable=False)
    comments = Column(Text, nullable=True)

    enqueued_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    last_seen_at = Column(DateTime, nullable=True)
    """
    Contains the timestamp, only when the job is not yet "finished", when the
    job last synchronised against the database, e.g., when it last checked the
    "cancel_flag" field.

    This is used for health checking whether the background worker is actually
    doing something, as a second line of defence to uncover "dropped" jobs,
    e.g., when the servers have failed and the new server can not identify
    jobs from its "previous life".
    """

    consumed = Column(Boolean, nullable=False,
                      default=False, server_default=false())
    """
    Whether the status of the job was checked **BY THE MAIN ACTOR** (username).
    """

    cancel_flag = Column(Boolean, nullable=False,
                         default=False, server_default=false())
    """
    Whether a SUPERUSER has signalled that the job should be cancelled.

    Note, that cancelling is a co-operative action: jobs are never actually
    "killed" on the O.S. level from the outside; rather, each job is expected
    to be implemented in a way that they regularly query this bit, and if set,
    act accordingly.
    """

    def __init__(self,
                 token: str,
                 kind: str,
                 summary: str,
                 machine_id: str,
                 user_name: Optional[str],
                 product: Optional[Product] = None,
                 ):
        self.machine_id = machine_id
        self.token = token
        self.kind = kind
        self.status = "allocated"
        self.summary = summary
        self.username = user_name
        self.last_seen_at = datetime.now(timezone.utc)

        if product:
            self.product_id = product.id

    def add_comment(self, comment: str, actor: Optional[str] = None):
        if not self.comments:
            self.comments = ""
        elif self.comments:
            self.comments += "\n----------\n"

        self.comments += f"{actor if actor else '<unknown>'} " \
            f"at {str(datetime.now(timezone.utc))}:\n{comment}"

    def heartbeat(self):
        """Update `last_seen_at`."""
        if self.status in ["enqueued", "running"]:
            self.last_seen_at = datetime.now(timezone.utc)

    def set_enqueued(self):
        """Marks the job as successfully enqueued."""
        if self.status != "allocated":
            raise ValueError(
                f"Invalid transition '{str(self.status)}' -> 'enqueued'")

        self.status = "enqueued"
        self.enqueued_at = datetime.now(timezone.utc)

    def set_running(self):
        """Marks the job as currently executing."""
        if self.status != "enqueued":
            raise ValueError(
                f"Invalid transition '{str(self.status)}' -> 'running'")

        self.status = "running"
        self.started_at = datetime.now(timezone.utc)

    def set_finished(self, successfully: bool = True):
        """Marks the job as successfully completed or failed."""
        new_status = "completed" if successfully else "failed"
        if self.status != "running":
            raise ValueError(
                f"Invalid transition '{str(self.status)}' -> '{new_status}'")

        self.status = new_status
        self.finished_at = datetime.now(timezone.utc)

    def set_abandoned(self, force_dropped_status: bool = False):
        """
        Marks the job as cancelled or dropped based on whether the
        cancel flag is set.
        """
        new_status = "cancelled" \
            if not force_dropped_status and self.cancel_flag \
            else "dropped"

        self.status = new_status
        self.finished_at = datetime.now(timezone.utc)

    @property
    def is_in_terminated_state(self) -> bool:
        """
        Returns whether the current task has finished execution in some way,
        for some reason.
        """
        return self.status not in ["allocated", "enqueued", "running"]

    @property
    def can_be_cancelled(self) -> bool:
        """
        Returns whether the task is in a state where setting `cancel_flag`
        is meaningful.
        """
        return not self.is_in_terminated_state and not self.cancel_flag


IDENTIFIER = {
    'identifier': "ConfigDatabase",
    'orm_meta': CC_META
}
