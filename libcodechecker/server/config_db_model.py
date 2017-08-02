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

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base

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


# class Superuser(Base):
#     __tablename__ = 'superusers'
#
#     id = Column(Integer, autoincrement=True, primary_key=True)
#     name = Column(String, nullable=False)
#     is_group = Column(Boolean, nullable=False)
#
#     def __init__(self, name, is_group):
#         self.name = name
#         self.is_group = is_group


class Product(Base):
    __tablename__ = 'products'

    __table_args__ = (
        UniqueConstraint('endpoint'),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    endpoint = Column(String, nullable=False)
    connection = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)

    def __init__(self, endpoint, conn_str, name=None):
        self.endpoint = endpoint
        self.connection = conn_str
        self.display_name = name if name else endpoint


# class ProductAdmin(Base):
#     __tablename__ = 'product_admins'
#
#     id = Column(Integer, autoincrement=True, primary_key=True)
#     product_id = Column(Integer,
#                         ForeignKey('products.id',
#                                    deferrable=False,
#                                    initially='IMMEDIATE',
#                                    ondelete='CASCADE'),
#                         nullable=False)
#     name = Column(String, nullable=False)
#     is_group = Column(Boolean, nullable=False)
#
#     def __init__(self, product_id, name, is_group):
#         self.product_id = product_id
#         self.name = name
#         self.is_group = is_group

IDENTIFIER = {
    'identifier': "ConfigDatabase",
    'orm_meta': CC_META,
    'version_class': DBVersion
}
