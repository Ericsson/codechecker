# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests for the product manager service.
"""

import sqlalchemy

import shared
from ProductManagement import ttypes

from libcodechecker.logger import LoggerFactory
from libcodechecker.profiler import timeit

from config_db_model import *

LOG = LoggerFactory.get_new_logger('PRODUCT HANDLER')


class ThriftProductHandler(object):
    """
    Connect to database and handle thrift client requests.
    """

    def __init__(self,
                 server,
                 config_session,
                 routed_product,
                 package_version):

        self.__server = server
        self.__package_version = package_version
        self.__session = config_session
        self.__product = routed_product

    @timeit
    def getAPIVersion(self):
        return shared.constants.API_VERSION

    @timeit
    def getPackageVersion(self):
        return self.__package_version

    @timeit
    def getProducts(self, product_endpoint_filter, product_name_filter):
        result = []

        try:
            session = self.__session()
            prods = session.query(Product)

            if product_endpoint_filter:
                prods = prods.filter(Product.endpoint.ilike(
                    '%{0}%'.format(product_endpoint_filter)))

            if product_name_filter:
                prods = prods.filter(Product.display_name.ilike(
                    '%{0}%'.format(product_name_filter)))

            prods = prods.all()

            for prod in prods:
                server_product = self.__server.get_product(prod.endpoint)
                result.append(ttypes.Product(
                    id=prod.id,
                    endpoint=prod.endpoint,
                    displayedName=prod.display_name,
                    description=prod.description,
                    connected=server_product.connected,
                    accessible=True))

            return result

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def getCurrentProduct(self):
        if not self.__product:
            msg = "Requested current product from ProductService but the " \
                  "request came through the main endpoint."
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)

        try:
            session = self.__session()
            prod = session.query(Product) \
                .filter(Product.id == self.__product.id).one()

            return ttypes.Product(id=prod.id,
                                  endpoint=prod.endpoint,
                                  displayedName=prod.display_name,
                                  description=prod.description)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()
