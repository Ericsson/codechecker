# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests for the product manager service.
"""

import base64
import os

import sqlalchemy

import shared
from ProductManagement import ttypes

from libcodechecker.logger import LoggerFactory
from libcodechecker.profiler import timeit

from config_db_model import *
from database_handler import SQLServer

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
        """
        Get the list of products configured on the server.
        """

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

                if not server_product:
                    # TODO: Better support this, if the configuration database
                    # is mounted to multiple servers?
                    LOG.error("Product '{0}' was found in the configuration "
                              "database, but no database connection is "
                              "present. Was the configuration database "
                              "connected to multiple servers?"
                              .format(prod.endpoint))
                    LOG.info("Please restart the server to make this "
                             "product available.")
                    continue

                # Clients are expected to use this method to query if
                # the product exists and usable. Usability sometimes requires
                # "updating" the "is connected" status of the database.
                if not server_product.connected:
                    server_product.connect()

                name = base64.b64encode(prod.display_name.encode('utf-8'))
                descr = base64.b64encode(prod.description.encode('utf-8')) \
                    if prod.description else None

                result.append(ttypes.Product(
                    id=prod.id,
                    endpoint=prod.endpoint,
                    displayedName_b64=name,
                    description_b64=descr,
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
        """
        Return information about the current product.

        The request MUST be routed as /product-name/ProductService!
        """

        if not self.__product:
            msg = "Requested current product from ProductService but the " \
                  "request came through the main endpoint."
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)

        try:
            session = self.__session()
            prod = session.query(Product).get(self.__product.id)

            server_product = self.__server.get_product(prod.endpoint)
            if not server_product:
                # TODO: Like above, better support this.
                LOG.error("Product '{0}' was found in the configuration "
                          "database, but no database connection is "
                          "present. Was the configuration database "
                          "connected to multiple servers?"
                          .format(prod.endpoint))
                LOG.info("Please restart the server to make this "
                         "product available.")
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE,
                    "Product exists, but was not connected to this server.")

            name = base64.b64encode(prod.display_name.encode('utf-8'))
            descr = base64.b64encode(prod.description.encode('utf-8')) \
                if prod.description else None

            return ttypes.Product(
                id=prod.id,
                endpoint=prod.endpoint,
                displayedName_b64=name,
                description_b64=descr,
                connected=server_product.connected,
                accessible=True)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def addProduct(self, product):
        """
        Add the given product to the products configured by the server.
        """

        LOG.info("User requested add product '{0}'".format(product.endpoint))

        dbc = product.connection
        if not dbc:
            msg = "Product cannot be added without a database configuration!"
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.GENERAL,
                                              msg)

        if self.__server.get_product(product.endpoint):
            msg = "A product endpoint '/{0}' is already configured!" \
                .format(product.endpoint)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.GENERAL,
                                              msg)

        # Some values come encoded as Base64, decode these.
        displayed_name = base64.b64decode(product.displayedName_b64)\
            .decode('utf-8') if product.displayedName_b64 else product.endpoint
        description = base64.b64decode(product.description_b64) \
            .decode('utf-8') if product.description_b64 else None

        dbuser = "codechecker"
        dbpass = ""
        if dbc.username_b64 and dbc.username_b64 != '':
            dbuser = base64.b64decode(dbc.username_b64)
        if dbc.password_b64 and dbc.password_b64 != '':
            dbpass = base64.b64decode(dbc.password_b64)

        if dbc.engine == 'sqlite' and not os.path.isabs(dbc.database):
            # Transform the database relative path to be under the
            # server's config directory.
            dbc.database = os.path.join(self.__server.config_directory,
                                        dbc.database)

        # Transform arguments into a database connection string.
        if dbc.engine == 'postgresql':
            conn_str_args = {'postgresql': True,
                             'sqlite': False,
                             'dbaddress': dbc.host,
                             'dbport': dbc.port,
                             'dbusername': dbuser,
                             'dbpassword': dbpass,
                             'dbname': dbc.database}
        elif dbc.engine == 'sqlite':
            conn_str_args = {'postgresql': False,
                             'sqlite': dbc.database}
        else:
            msg = "Database engine '{0}' unknown!".format(dbc.engine)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.GENERAL,
                                              msg)

        conn_str = SQLServer \
            .from_cmdline_args(conn_str_args, IDENTIFIER, None, False, None) \
            .get_connection_string()

        # Create the product's entity in the database.
        try:
            orm_prod = Product(
                endpoint=product.endpoint,
                conn_str=conn_str,
                name=displayed_name,
                description=description)

            LOG.debug("Attempting database connection to new product...")

            # Connect and create the database schema.
            self.__server.add_product(orm_prod)
            LOG.debug("Product database successfully connected to.")

            connection_wrapper = self.__server.get_product(product.endpoint)
            if connection_wrapper.last_connection_failure:
                msg = "The configured connection for '/{0}' failed: {1}" \
                    .format(product.endpoint,
                            connection_wrapper.last_connection_failure)
                LOG.error(msg)

                self.__server.remove_product(product.endpoint)

                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.IOERROR, msg)

            session = self.__session()
            session.add(orm_prod)
            session.commit()
            LOG.debug("Product configuration added to database successfully.")

            # The orm_prod object above is not bound to the database as it
            # was just created. We use the actual database-backed configuration
            # entry to handle connections, so a "reconnect" is issued here.
            self.__server.remove_product(product.endpoint)

            orm_prod = session.query(Product) \
                .filter(Product.endpoint == product.endpoint).one()
            self.__server.add_product(orm_prod)

            LOG.debug("Product database connected and ready to serve.")
            return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            if session:
                session.close()

    @timeit
    def removeProduct(self, product_id):
        """
        Disconnect the product specified by the ID from the server.
        """

        try:
            session = self.__session()
            product = session.query(Product).get(product_id)
            if product is None:
                msg = "Product with ID {0} does not exist!".format(product_id)
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE,
                    msg)

            LOG.info("User requested to remove product '{0}'"
                     .format(product.endpoint))
            self.__server.remove_product(product.endpoint)

            session.delete(product)
            session.commit()
            return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()
