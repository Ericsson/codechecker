# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handle Thrift requests for the product manager service.
"""


import os
import random

from sqlalchemy.sql.expression import and_

import codechecker_api_shared
from codechecker_api.ProductManagement_v6 import ttypes

from codechecker_common.logger import get_logger

from codechecker_server.profiler import timeit
from codechecker_web.shared import convert

from .. import permissions
from ..database.config_db_model import IDENTIFIER, Product, ProductPermission
from ..database.database import DBSession, SQLServer, conv, escape_like
from ..routing import is_valid_product_endpoint

from .thrift_enum_helper import confidentiality_enum, \
        confidentiality_str

LOG = get_logger('server')


class ThriftProductHandler:
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

        with DBSession(self.__session) as session:
            if args is None:
                args = dict(self.__permission_args)
                args['config_db_session'] = session

            if not any([permissions.require_permission(
                            perm, args, self.__auth_session)
                        for perm in required]):
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You are not authorized to execute this action.")

            return True

    def __administrating(self, args):
        """ True if the current user can administrate the given product. """
        if permissions.require_permission(permissions.SUPERUSER, args,
                                          self.__auth_session):
            return True

        if permissions.require_permission(permissions.PRODUCT_ADMIN, args,
                                          self.__auth_session):
            return True

        return False

    def __get_product(self, session, product):
        """
        Retrieve the product connection object and create a Thrift Product
        object for the given product record in the database.
        """

        server_product = self.__server.get_product(product.endpoint)
        if not server_product:
            LOG.info("Product '%s' was found in the configuration "
                     "database but no database connection was "
                     "present. Mounting analysis run database...",
                     product.endpoint)
            self.__server.add_product(product)
            server_product = self.__server.get_product(product.endpoint)

        descr = convert.to_b64(product.description) \
            if product.description else None

        args = {'config_db_session': session,
                'productID': product.id}
        product_access = permissions.require_permission(
            permissions.PRODUCT_VIEW, args, self.__auth_session)

        admin_perm_name = permissions.PRODUCT_ADMIN.name
        admins = session.query(ProductPermission). \
            filter(and_(ProductPermission.permission == admin_perm_name,
                        ProductPermission.product_id == product.id)) \
            .all()

        connected = server_product.db_status ==\
            codechecker_api_shared.ttypes.DBStatus.OK

        latest_storage_date = str(product.latest_storage_date) \
            if product.latest_storage_date else None

        if product.confidentiality is None:
            confidentiality = ttypes.Confidentiality.CONFIDENTIAL
        else:
            confidentiality = \
                    confidentiality_enum(product.confidentiality)

        return server_product, ttypes.Product(
            id=product.id,
            endpoint=product.endpoint,
            displayedName_b64=convert.to_b64(product.display_name),
            description_b64=descr,
            runCount=product.num_of_runs,
            latestStoreToProduct=latest_storage_date,
            connected=connected,
            accessible=product_access,
            administrating=self.__administrating(args),
            databaseStatus=server_product.db_status,
            admins=[admin.name for admin in admins],
            confidentiality=confidentiality)

    @timeit
    def getPackageVersion(self):
        return self.__package_version

    @timeit
    def isAdministratorOfAnyProduct(self):
        with DBSession(self.__session) as session:
            prods = session.query(Product).all()

            for prod in prods:
                args = {'config_db_session': session,
                        'productID': prod.id}
                if permissions.require_permission(
                        permissions.PRODUCT_ADMIN,
                        args, self.__auth_session):
                    return True

            return False

    @timeit
    def getProducts(self, product_endpoint_filter, product_name_filter):
        """
        Get the list of products configured on the server.
        """

        result = []

        with DBSession(self.__session) as session:
            prods = session.query(Product)

            num_all_products = prods.count()  # prods get filtered later.
            if num_all_products < self.__server.num_products:
                # It can happen that a product gets removed from the
                # configuration database from a different server that uses the
                # same configuration database. In this case, the product is
                # no longer valid, yet the current server keeps a connection
                # object up.
                LOG.info("%d products were removed but server is still "
                         "connected to them. Disconnecting these...",
                         self.__server.num_products - num_all_products)

                all_products = session.query(Product).all()
                self.__server.remove_products_except([prod.endpoint for prod
                                                      in all_products])

            if product_endpoint_filter:
                prods = prods.filter(Product.endpoint.ilike(
                    conv(escape_like(product_endpoint_filter, '\\')),
                    escape='\\'))

            if product_name_filter:
                prods = prods.filter(Product.display_name.ilike(
                    conv(escape_like(product_name_filter, '\\')),
                    escape='\\'))

            prods = prods.all()
            for prod in prods:
                _, ret = self.__get_product(session, prod)
                result.append(ret)

            return result

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
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.IOERROR,
                msg)

        with DBSession(self.__session) as session:
            prod = session.query(Product).get(self.__product.id)

            if not prod:
                msg = "The product requested has been disconnected from the " \
                      "server."
                LOG.error(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.IOERROR,
                    msg)

            _, ret = self.__get_product(session, prod)
            LOG.debug(ret)
            return ret

    @timeit
    def getProductConfiguration(self, product_id):
        """
        Get the product configuration --- WITHOUT THE DB PASSWORD --- of the
        given product.
        """

        with DBSession(self.__session) as session:
            product = session.query(Product).get(product_id)
            if product is None:
                msg = "Product with ID {0} does not exist!".format(product_id)
                LOG.error(msg)

                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

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
                username_b64=convert.to_b64(db_user),
                # DO NOT TRANSPORT PASSWORD BACK TO THE USER!
                database=db_name)

            # Put together the product configuration.
            descr = convert.to_b64(product.description) \
                if product.description else None

            is_review_status_change_disabled = \
                product.is_review_status_change_disabled

            if product.confidentiality is None:
                confidentiality = ttypes.Confidentiality.CONFIDENTIAL
            else:
                confidentiality = \
                        confidentiality_enum(product.confidentiality)

            prod = ttypes.ProductConfiguration(
                id=product.id,
                endpoint=product.endpoint,
                displayedName_b64=convert.to_b64(product.display_name),
                description_b64=descr,
                connection=dbc,
                runLimit=product.run_limit,
                isReviewStatusChangeDisabled=is_review_status_change_disabled,
                confidentiality=confidentiality)

            return prod

    @timeit
    def addProduct(self, product):
        """
        Add the given product to the products configured by the server.
        """
        self.__require_permission([permissions.SUPERUSER])

        session = None
        LOG.info("User requested add product '%s'", product.endpoint)

        if not is_valid_product_endpoint(product.endpoint):
            msg = "The specified endpoint is invalid."
            LOG.error(msg)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                msg)

        dbc = product.connection
        if not dbc:
            msg = "Product cannot be added without a database configuration!"
            LOG.error(msg)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                msg)

        if self.__server.get_product(product.endpoint):
            msg = "A product endpoint '/{0}' is already configured!" \
                .format(product.endpoint)
            LOG.error(msg)
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                msg)

        # Some values come encoded as Base64, decode these.
        displayed_name = convert.from_b64(product.displayedName_b64) \
            if product.displayedName_b64 else product.endpoint
        description = convert.from_b64(product.description_b64) \
            if product.description_b64 else None

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
                dbuser = convert.from_b64(dbc.username_b64)
            if dbc.password_b64 and dbc.password_b64 != '':
                dbpass = convert.from_b64(dbc.password_b64)

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
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.GENERAL,
                msg)

        conn_str = SQLServer \
            .from_cmdline_args(conn_str_args, IDENTIFIER, None, False, None) \
            .get_connection_string()

        is_rws_change_disabled = product.isReviewStatusChangeDisabled

        confidentiality = confidentiality_str(product.confidentiality)

        # Create the product's entity in the database.
        with DBSession(self.__session) as session:
            orm_prod = Product(
                endpoint=product.endpoint,
                conn_str=conn_str,
                name=displayed_name,
                description=description,
                run_limit=product.runLimit,
                is_review_status_change_disabled=is_rws_change_disabled,
                confidentiality=confidentiality)

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

                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.IOERROR, msg)

            LOG.debug("Product database successfully connected to.")
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

    @timeit
    def editProduct(self, product_id, new_config):
        """
        Edit the given product's properties to the one specified by
        new_configuration.
        """
        with DBSession(self.__session) as session:
            product = session.query(Product).get(product_id)
            if product is None:
                msg = "Product with ID {0} does not exist!".format(product_id)
                LOG.error(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

            # Editing the metadata of the product, such as display name and
            # description is available for product admins.

            # Because this query doesn't come through a product endpoint,
            # __init__ sets the value in the extra_args to None.
            self.__permission_args['productID'] = product.id
            self.__require_permission([permissions.PRODUCT_ADMIN])

            LOG.info("User requested edit product '%s'",
                     product.endpoint)

            dbc = new_config.connection
            if not dbc:
                msg = "Product's database configuration cannot be removed!"
                LOG.error(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.GENERAL, msg)

            if new_config.endpoint != product.endpoint:
                if not is_valid_product_endpoint(new_config.endpoint):
                    msg = "The endpoint to move the product to is invalid."
                    LOG.error(msg)
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.GENERAL, msg)

                if self.__server.get_product(new_config.endpoint):
                    msg = f"A product endpoint '/{product.endpoint}' is " \
                          f"already configured!"
                    LOG.error(msg)
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.GENERAL, msg)

                LOG.info("User renamed product '%s' to '%s'",
                         product.endpoint, new_config.endpoint)

            # Some values come encoded as Base64, decode these.
            displayed_name = convert.from_b64(new_config.displayedName_b64) \
                if new_config.displayedName_b64 \
                else new_config.endpoint
            description = convert.from_b64(new_config.description_b64) \
                if new_config.description_b64 else None

            confidentiality = confidentiality_str(new_config.confidentiality)

            if dbc.engine == 'sqlite' and not os.path.isabs(dbc.database):
                # Transform the database relative path to be under the
                # server's config directory.
                dbc.database = os.path.join(self.__server.config_directory,
                                            dbc.database)

            # Transform arguments into a database connection string.
            if dbc.engine == 'postgresql':
                dbuser = "codechecker"
                if dbc.username_b64 and dbc.username_b64 != '':
                    dbuser = convert.from_b64(dbc.username_b64)

                old_connection_args = SQLServer.connection_string_to_args(
                        product.connection)
                if dbc.password_b64 and dbc.password_b64 != '':
                    dbpass = convert.from_b64(dbc.password_b64)
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
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.GENERAL,
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

                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.IOERROR, msg)

                # The orm_prod object above is not bound to the database as it
                # was just created. We use the actual database-backed
                # configuration entry to handle connections, so a "reconnect"
                # is issued later.
                self.__server.remove_product(dummy_endpoint)

            # Update the settings in the database.
            product.endpoint = new_config.endpoint
            product.run_limit = new_config.runLimit
            product.is_review_status_change_disabled = \
                new_config.isReviewStatusChangeDisabled
            product.connection = conn_str
            product.display_name = displayed_name
            product.description = description
            product.confidentiality = confidentiality

            session.commit()
            LOG.info("Product configuration edited and saved successfully.")

            if product_needs_reconnect:
                product = session.query(Product).get(product_id)
                LOG.info("Product change requires database reconnection...")

                LOG.debug("Disconnecting...")
                try:
                    # Because of the process pool it is possible that in the
                    # local cache of the current process the product with the
                    # old endpoint is not found and it will raise an exception.
                    self.__server.remove_product(old_endpoint)
                except ValueError:
                    pass

                LOG.debug("Connecting new settings...")
                self.__server.add_product(product)

                LOG.info("Product reconnected successfully.")

            return True

    @timeit
    def removeProduct(self, product_id):
        """
        Disconnect the product specified by the ID from the server.
        """
        self.__require_permission([permissions.SUPERUSER])

        with DBSession(self.__session) as session:
            product = session.query(Product).get(product_id)
            if product is None:
                msg = "Product with ID {0} does not exist!".format(product_id)
                LOG.error(msg)

                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE, msg)

            LOG.info("User requested to remove product '%s'", product.endpoint)
            self.__server.remove_product(product.endpoint)

            session.delete(product)
            session.commit()
            return True
