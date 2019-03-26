PostgreSQL
==========

This guide covers the extra installation and configuration steps required to
run CodeChecker servers with a PostgreSQL database as backend.

Alternatively, and by default, CodeChecker uses SQLite as database backend,
and these steps are not mandatory for a successful installation.

Table of Contents
=================
* [List of runtime dependencies](#list-of-runtime-dependencies)
* [Installing dependencies and setting up a server](#installing-dependencies)
* [Creating analysis databases](#creating-analysis-databases)

## <a name="list-of-runtime-dependencies"></a> List of runtime dependencies

 *  [PostgreSQL](http://www.postgresql.org) (> `9.3.5`)
    (optional)
 *  At least one database connector library for PostgreSQL support required:
    - [psycopg2](http://initd.org/psycopg) (> `2.5.4`) or
    - [pg8000](https://github.com/mfenniak/pg8000) (>= `1.10.0`)
    - [PyPi psycopg2](https://pypi.python.org/pypi/psycopg2/2.6.1)
      **(Requires `lbpq`!)**
    - [PyPi pg8000](https://pypi.python.org/pypi/pg8000)

# Installing dependencies and setting up a server <a name="installing-dependencies"></a>
Tested on Ubuntu LTS `14.04.2`.

~~~~~~{.sh}
# Get the extra PostgreSQL packages.
sudo apt-get install libpq-dev postgresql \
  postgresql-client-common postgresql-common \
  python-dev

# Setup databases for CodeChecker.
#
# By default, only the installer-created 'postgres' user has access to
# database-specific binaries and actions.

# Switch to this daemon user.
sudo -i -u postgres

# Create a new user to be used for connecting to the database.
# (The password will be prompted for, and read from the standard input.)
createuser --login --pwprompt codechecker

# NOTE: For production systems, certain extra access control configuration
# should be done to make sure database access is secure. Refer to the
# PostgreSQL manual on connection control.

# Create the configuration database for CodeChecker.
createdb codechecker_config

# The newly created user must have privileges on its own database.
psql -c "GRANT ALL PRIVILEGES ON DATABASE codechecker_config TO codechecker;"

# Return to your normal shell via:
exit

# PGPASSFILE environment variable should be set to a 'pgpass' file.
# For format and further information see PostgreSQL documentation:
# http://www.postgresql.org/docs/current/static/libpq-pgpass.html

echo "*:5432:*:codechecker:my_password" >> ~/.pgpass
chmod 0600 ~/.pgpass
~~~~~~

> For format and further information on `pgpass` files, please refer to the
> [PostgreSQL documentation](http://www.postgresql.org/docs/current/static/libpq-pgpass.html).

At this point, you can normal continue with installing the necessary Python
requirements and creating an install of CodeChecker:

~~~~~~{.sh}
# Set the created virtualenv as your environment.
source $PWD/venv/bin/activate

# Build and install a CodeChecker package.
make package

# For ease of access, add the build directory to PATH.
export PATH="$PWD/build/CodeChecker/bin:$PATH"
~~~~~~

Once the package is installed and the PostgreSQL server is running, a
CodeChecker server can be started by specifying the **configuration**
database's connection arguments. (Read more about the [`CodeChecker server`
command](user_guide.md#server).)

The `codechecker_config` database will contain server-specific configurations.

~~~~~~{.sh}
CodeChecker server --postgresql \
  --db-host localhost --db-port 5432 \
  --db-username codechecker --db-name codechecker_config
~~~~~~

# Creating analysis databases <a name="creating-analysis-databases"></a>

At least one additional database must be created in which analysis reports
will be stored. (Unlike the default SQLite mode, creation of this *Default*
product is **not automatic** when PostgreSQL is used!)

~~~~~~{.sh}
# Switch to the daemon user.
sudo -i -u postgres

# Create database and give rights to the server user.
createdb default_product

# The newly created user must have privileges on its own database.
psql -c "GRANT ALL PRIVILEGES ON DATABASE default_product TO codechecker;"
~~~~~~

For a product to be set up by the server, an empty database with rights given
must exist **in advance**. Once the database is created, a product can be
added via `CodeChecker cmd products add`, or
[via the Web interface](products.md#managing-products-through-the-web-interface).

~~~~~~{.sh}
CodeChecker cmd products add Default --name "Default Product" \
  --postgresql \
  --db-host localhost --db-port 5432 \
  --db-username codechecker --db-name default_product
~~~~~~

Once the product is configured, normal operations, such as `store` and
browsing the results in the Web application, can commence.
