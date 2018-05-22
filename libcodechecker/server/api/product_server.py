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
import random

import sqlalchemy
from sqlalchemy.sql.expression import and_

import shared
from ProductManagement_v6 import ttypes

from libcodechecker import util
from libcodechecker.logger import get_logger
from libcodechecker.profiler import timeit
from libcodechecker.server import permissions
from libcodechecker.server.database.config_db_model import IDENTIFIER, \
    Product, ProductPermission
from libcodechecker.server.database.database import SQLServer, conv
from libcodechecker.server.database.run_db_model import Run
from libcodechecker.server.routing import is_valid_product_endpoint

LOG = get_logger('server')


class ThriftProductHandler(object):
    """
    Connect to database and handle thrift client requests.
    """

    def __init__(self,
                 server,
                 auth_session,
                 config_session,
                 routed_product,
                 package_version):

        self.__server = server
        self.__auth_session = auth_session
        self.__package_version = package_version
        self.__session = config_session
        self.__product = routed_product

        self.__permission_args = {
            'productID': routed_product.id if routed_product else None
        }

    def __require_permission(self, required, args=None):
        """
        Helper method to raise an UNAUTHORIZED exception if the user does not
        have any of the given permissions.
        """

        try:
            if args is None:
                args = dict(self.__permission_args)
                session = self.__session()
                args['config_db_session'] = session

            if not any([permissions.require_permission(
                            perm, args, self.__auth_session)
                        for perm in required]):
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You are not authorized to execute this action.")

            return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            if session:
                session.close()

    def __get_product(self, session, product):
        """
        Retrieve the product connection object and create a Thrift Product
        object for the given product record in the database.
        """

        server_product = self.__server.get_product(product.endpoint)
        if not server_product:
            LOG.info("Product '{0}' was found in the configuration "
                     "database but no database connection was "
                     "present. Mounting analysis run database..."
                     .format(product.endpoint))
            self.__server.add_product(product)
            server_product = self.__server.get_product(product.endpoint)

        server_product.connect()
        num_of_runs = 0
        latest_store_to_product = ""
        if server_product.db_status == shared.ttypes.DBStatus.OK:
            run_db_session = server_product.session_factory()
            num_of_runs = run_db_session.query(Run).count()
            if num_of_runs:
                last_updated_run = run_db_session.query(Run) \
                    .order_by(Run.date.desc()) \
                    .limit(1) \
                    .one_or_none()

                latest_store_to_product = last_updated_run.date

        name = base64.b64encode(product.display_name.encode('utf-8'))
        descr = base64.b64encode(product.description.encode('utf-8')) \
            if product.description else None

        args = {'config_db_session': session,
                'productID': product.id}
        product_access = permissions.require_permission(
            permissions.PRODUCT_ACCESS, args, self.__auth_session)
        product_admin = permissions.require_permission(
            permissions.PRODUCT_ADMIN, args, self.__auth_session)

        admin_perm_name = permissions.PRODUCT_ADMIN.name
        admins = session.query(ProductPermission). \
            filter(and_(ProductPermission.permission == admin_perm_name,
                        ProductPermission.product_id == product.id)) \
            .all()

        return server_product, ttypes.Product(
            id=product.id,
            endpoint=product.endpoint,
            displayedName_b64=name,
            description_b64=descr,
            runCount=num_of_runs,
            latestStoreToProduct=str(latest_store_to_product),
            connected=server_product.db_status == shared.ttypes.DBStatus.OK,
            accessible=product_access,
            administrating=product_admin,
            databaseStatus=server_product.db_status,
            admins=[admin.name for admin in admins])

    @timeit
    def getPackageVersion(self):
        return self.__package_version

    @timeit
    def isAdministratorOfAnyProduct(self):
        try:
            session = self.__session()
            prods = session.query(Product).all()

            for prod in prods:
                args = {'config_db_session': session,
                        'productID': prod.id}
                if permissions.require_permission(
                        permissions.PRODUCT_ADMIN,
                        args, self.__auth_session):
                    return True

            return False

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def getProducts(self, product_endpoint_filter, product_name_filter):
        """
        Get the list of products configured on the server.
        """

        result = []

        try:
            session = self.__session()
            prods = session.query(Product)

            num_all_products = prods.count()  # prods get filtered later.
            if num_all_products < self.__server.num_products:
                # It can happen that a product gets removed from the
                # configuration database from a different server that uses the
                # same configuration database. In this case, the product is
                # no longer valid, yet the current server keeps a connection
                # object up.
                LOG.info("{0} products were removed but server is still "
                         "connected to them. Disconnecting these...".format(
                             self.__server.num_products - num_all_products))

                all_products = session.query(Product).all()
                self.__server.remove_products_except([prod.endpoint for prod
                                                      in all_products])

            if product_endpoint_filter:
                prods = prods.filter(Product.endpoint.ilike(
                    conv(util.escape_like(product_endpoint_filter, '\\')),
                    escape='\\'))

            if product_name_filter:
                prods = prods.filter(Product.display_name.ilike(
                    conv(util.escape_like(product_name_filter, '\\')),
                    escape='\\'))

            prods = prods.all()
            for prod in prods:
                _, ret = self.__get_product(session, prod)
                result.append(ret)

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

            if not prod:
                msg = "The product requested has been disconnected from the " \
                      "server."
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.IOERROR,
                    msg)

            _, ret = self.__get_product(session, prod)
            return ret
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def getProductConfiguration(self, product_id):
        """
        Get the product configuration --- WITHOUT THE DB PASSWORD --- of the
        given product.
        """

        try:
            session = self.__session()
            product = session.query(Product).get(product_id)
            if product is None:
                msg = "Product with ID {0} does not exist!".format(product_id)
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

            # Put together the database connection's descriptor.
            args = SQLServer.connection_string_to_args(product.connection)
            if args['postgresql']:
                db_engine = 'postgresql'
                db_host = args['dbaddress']
                db_port = args['dbport']
                db_user = args['dbusername']
                db_name = args['dbname']
            else:
                db_engine = 'sqlite'
                db_host = ""
                db_port = 0
                db_user = ""
                db_name = args['sqlite']

            dbc = ttypes.DatabaseConnection(
                engine=db_engine,
                host=db_host,
                port=db_port,
                username_b64=base64.b64encode(db_user),
                # DO NOT TRANSPORT PASSWORD BACK TO THE USER!
                database=db_name)

            # Put together the product configuration.
            name = base64.b64encode(product.display_name.encode('utf-8'))
            descr = base64.b64encode(product.description.encode('utf-8')) \
                if product.description else None

            prod = ttypes.ProductConfiguration(
                id=product.id,
                endpoint=product.endpoint,
                displayedName_b64=name,
                description_b64=descr,
                connection=dbc,
                runLimit=product.run_limit)

            return prod

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
        self.__require_permission([permissions.SUPERUSER])

        session = None
        LOG.info("User requested add product '{0}'".format(product.endpoint))

        if not is_valid_product_endpoint(product.endpoint):
            msg = "The specified endpoint is invalid."
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.GENERAL,
                                              msg)

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

        if dbc.engine == 'sqlite' and not os.path.isabs(dbc.database):
            # Transform the database relative path to be under the
            # server's config directory.
            dbc.database = os.path.join(self.__server.config_directory,
                                        dbc.database)

        # Transform arguments into a database connection string.
        if dbc.engine == 'postgresql':
            dbuser = "codechecker"
            dbpass = ""
            if dbc.username_b64 and dbc.username_b64 != '':
                dbuser = base64.b64decode(dbc.username_b64)
            if dbc.password_b64 and dbc.password_b64 != '':
                dbpass = base64.b64decode(dbc.password_b64)

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
                description=description,
                run_limit=product.runLimit)

            LOG.debug("Attempting database connection to new product...")

            # Connect and create the database schema.
            self.__server.add_product(orm_prod, init_db=True)
            connection_wrapper = self.__server.get_product(product.endpoint)
            if connection_wrapper.last_connection_failure:
                msg = "The configured connection for '/{0}' failed: {1}" \
                    .format(product.endpoint,
                            connection_wrapper.last_connection_failure)
                LOG.error(msg)

                self.__server.remove_product(product.endpoint)

                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.IOERROR, msg)

            LOG.debug("Product database successfully connected to.")
            session = self.__session()
            session.add(orm_prod)
            session.flush()

            # Create the default permissions for the product
            permissions.initialise_defaults('PRODUCT', {
                'config_db_session': session,
                'productID': orm_prod.id
            })
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
    def editProduct(self, product_id, new_config):
        """
        Edit the given product's properties to the one specified by
        new_configuration.
        """
        try:
            session = self.__session()
            product = session.query(Product).get(product_id)
            if product is None:
                msg = "Product with ID {0} does not exist!".format(product_id)
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

            # Editing the metadata of the product, such as display name and
            # description is available for product admins.

            # Because this query doesn't come through a product endpoint,
            # __init__ sets the value in the extra_args to None.
            self.__permission_args['productID'] = product.id
            self.__require_permission([permissions.PRODUCT_ADMIN])

            LOG.info("User requested edit product '{0}'"
                     .format(product.endpoint))

            dbc = new_config.connection
            if not dbc:
                msg = "Product's database configuration cannot be removed!"
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.GENERAL, msg)

            if new_config.endpoint != product.endpoint:
                if not is_valid_product_endpoint(new_config.endpoint):
                    msg = "The endpoint to move the product to is invalid."
                    LOG.error(msg)
                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.GENERAL, msg)

                if self.__server.get_product(new_config.endpoint):
                    msg = "A product endpoint '/{0}' is already configured!" \
                          .format(product.endpoint)
                    LOG.error(msg)
                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.GENERAL, msg)

                LOG.info("User renamed product '{0}' to '{1}'"
                         .format(product.endpoint, new_config.endpoint))

            # Some values come encoded as Base64, decode these.
            displayed_name = base64.b64decode(new_config.displayedName_b64) \
                .decode('utf-8') if new_config.displayedName_b64 \
                else new_config.endpoint
            description = base64.b64decode(new_config.description_b64) \
                .decode('utf-8') if new_config.description_b64 else None

            if dbc.engine == 'sqlite' and not os.path.isabs(dbc.database):
                # Transform the database relative path to be under the
                # server's config directory.
                dbc.database = os.path.join(self.__server.config_directory,
                                            dbc.database)

            # Transform arguments into a database connection string.
            if dbc.engine == 'postgresql':
                dbuser = "codechecker"
                if dbc.username_b64 and dbc.username_b64 != '':
                    dbuser = base64.b64decode(dbc.username_b64)

                old_connection_args = SQLServer.connection_string_to_args(
                        product.connection)
                if dbc.password_b64 and dbc.password_b64 != '':
                    dbpass = base64.b64decode(dbc.password_b64)
                elif 'dbpassword' in old_connection_args:
                    # The password was not changed. Retrieving from old
                    # configuration -- if the old configuration contained such!
                    dbpass = old_connection_args['dbpassword']
                else:
                    dbpass = None

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
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.GENERAL,
                    msg)

            conn_str = SQLServer \
                .from_cmdline_args(conn_str_args, IDENTIFIER, None,
                                   False, None).get_connection_string()

            # If endpoint or database arguments change, the product
            # configuration has changed so severely, that it needs
            # to be reconnected.
            product_needs_reconnect = \
                product.endpoint != new_config.endpoint or \
                product.connection != conn_str
            old_endpoint = product.endpoint

            if product_needs_reconnect:
                # Changing values that alter connection-specific data
                # should only be available for superusers!
                self.__require_permission([permissions.SUPERUSER])

                # Test if the new database settings are correct or not.
                dummy_endpoint = new_config.endpoint + '_' + ''.join(
                    random.sample(new_config.endpoint,
                                  min(len(new_config.endpoint), 5)))
                dummy_prod = Product(
                    endpoint=dummy_endpoint,
                    conn_str=conn_str,
                    name=displayed_name,
                    description=description)

                LOG.debug("Attempting database connection with new "
                          "settings...")

                # Connect and create the database schema.
                self.__server.add_product(dummy_prod)
                LOG.debug("Product database successfully connected to.")

                connection_wrapper = self.__server.get_product(dummy_endpoint)
                if connection_wrapper.last_connection_failure:
                    msg = "The configured connection for '/{0}' failed: {1}" \
                        .format(new_config.endpoint,
                                connection_wrapper.last_connection_failure)
                    LOG.error(msg)

                    self.__server.remove_product(dummy_endpoint)

                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.IOERROR, msg)

                # The orm_prod object above is not bound to the database as it
                # was just created. We use the actual database-backed
                # configuration entry to handle connections, so a "reconnect"
                # is issued later.
                self.__server.remove_product(dummy_endpoint)

            # Update the settings in the database.
            product.endpoint = new_config.endpoint
            product.run_limit = new_config.runLimit
            product.connection = conn_str
            product.display_name = displayed_name
            product.description = description

            session.commit()
            LOG.info("Product configuration edited and saved successfully.")

            if product_needs_reconnect:
                product = session.query(Product).get(product_id)
                LOG.info("Product change requires database reconnection...")

                LOG.debug("Disconnecting...")
                self.__server.remove_product(old_endpoint)

                LOG.debug("Connecting new settings...")
                self.__server.add_product(product)

                LOG.info("Product reconnected successfully.")

            return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def removeProduct(self, product_id):
        """
        Disconnect the product specified by the ID from the server.
        """
        self.__require_permission([permissions.SUPERUSER])

        try:
            session = self.__session()
            product = session.query(Product).get(product_id)
            if product is None:
                msg = "Product with ID {0} does not exist!".format(product_id)
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

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
