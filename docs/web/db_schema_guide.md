# How to modify the database schema

CodeChecker is developed in rolling release model so it is important to update
the database schema in a backward compatible way. This is achieved using the
[Alembic](https://alembic.sqlalchemy.org/en/latest/index.html) database
migration tool.

CodeChecker uses [SQLAlchemy](http://www.sqlalchemy.org/) for database
operations. Please read [SQLAlchemy declarative syntax documentation](http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/)
for syntax and semantics.

Alembic can compare the table metadata against the status of a database and
based on this comparison it generates the migration script. Even though this
method has it's [limitations](
https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect)
, in most cases it works well.

# Updating configuration database schema

Config database schema scripts can be found under the `config_db_migrate`
directory.

## Automatic migration script generation (Online)

A Codechecker server should be started with the previous database schema
version.

### **Step 1**: Update the database model

The configuration database schema file can be found here:
`server/codechecker_server/database/config_db_model.py`

### **Step 2**: Check the alembic.ini configuration settings

Database connection should point to the correct database.
Edit the sqlalchemy.url option in [alembic.ini](
   https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file)
   according to your database configuration.

### **Step 3**: Use alembic to autogenerate migration scripts

`alembic --name config_db revision --autogenerate -m "Change description"`

### **Step 4**: Check the generated scripts
The new migration script
`config_db_migrate/versions/{hash}_change_description.py` is generated.
**You must always check the generated script because sometimes it isn't
correct.**

### **Step 5**: Run all test cases.

**All tests must pass!**

### **Step 6**: Commit the new version files.

Don't forget to commit the migration script with your other changes.


# Updating the run database

## Automatic migration script generation (Online)

A Codechecker server should be started and a product should be configured with
a previous database schema version.

### **Step 1**: Update the database model

The run database schema file can be found here:
`server/codechecker_server/database/run_db_model.py`

### **Step 2**: Check alembic.ini configuration

Database connection should point to the correct database.
Edit the sqlalchemy.url option in [alembic.ini](
   https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file)
   according to your database configuration.

#### **Step 2**: Generating migration scripts using autogenerate

`alembic --name run_db revision --autogenerate -m "Change description"`

#### **Step 3**: Check the generated scripts
The new migration script db_migrate/versions/{hash}_change_description.py is
   generated. **You must always check the generated script because sometimes it
   isn't correct.**

#### **Step 4**: Run all test cases.

**All tests must pass!**

#### **Step 5**: Commit the new version files.

Don't forget to commit the migration script with your other changes.

# Writing migration scripts by hand

Navigate to the root directory of CodeChecker source code and create an empty
migration script using `alembic revision`:

`alembic --name run_db revision -m "Change description"`

The new file
`server/codechecker_server/migrations/report/versions/{hash}_change_description.py`
is generated. This file contains an empty `upgrade` and a `downgrade` function.

The empty `upgrade` and `downgrade` should be written by hand.


# Database upgrade for running servers

It is possible that a new release introduces database changes and database
schema migration is required.

There are two database types which might need schema migration.
One of them is the configuration database (storing product configurations)
and the other is the run database (storing analysis reports).

If there is some schema mismatch and migration is needed you will get a
warning at server start.

## IMPORTANT before schema upgrade

If there is some schema change it is recommended to create a full backup
of your configuration and run databases before running the migration.
If there is some error during the migration you can still restore the
previous version and there will be no data loss.

### Migration at server start

Schema migration can be done at server start. The database for the config
and product databases will be automatically checked. If there are databases
which can be upgraded you will be asked if you want to upgrade the schema to
the latest version.

NOTE: Before running the migration you should make a full backup of your
config and product databases!

The config database location will be printed first at the server start.
Migration of the config database is done independently from the product
databases. The product database locations can be viewed with the
`CodeChecker server --db-status all` command.

## Checking if migration will be required.

Running the `CodeChecker server --db-status all` command with the new
CodeChecker release will show you if database upgrade is needed for the new
release.

NOTE: Use the same arguments which were used to start the server to check
the status. It is required to find the used configuration database.

```sh
$ CodeChecker server --db-status all
[15:01] - Checking configuration database ...
[15:01] - Database is OK.
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Product endpoint | Database status                                | Database location              | Schema version in the database | Schema version in the package
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Default          | Database is up to date.                        | ~/.codechecker/Default.sqlite  | 82ca43f05c10 (up to date)      | 82ca43f05c10
Default2         | Database schema mismatch! Possible to upgrade. | ~/.codechecker/Default2.sqlite | 82ca43f05c10                   | f1f7600168dc
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

## Upgrade configuration database

The configuration database migration can be done at server start.
A prompt will ask you if you want to proceed with the schema upgrade.

NOTE: After the configuration database was upgraded only the newer CodeChecker
releases will be able to read up the configuration. The older versions will
fail to start.

## Upgrade product databases

### Check if migration is possible

With the `CodeChecker server --db-status all` the database statuses for all of
the product databases can be checked.

### Product migration

Schema upgrade can be done for each product independently or in a row for all
of the products with the `CodeChecker server --db-upgrade-schema PRODUCT_NAME`
command.

```sh
$ CodeChecker server --db-upgrade-schema Default
[15:01] - Checking configuration database ...
[15:01] - Database is OK.
[15:01] - Preparing schema upgrade for Default
[WARNING] [15:01] - Please note after migration only newer CodeChecker versions can be used to start the server
[WARNING] [15:01] - It is advised to make a full backup of your run databases.
[15:01] - ========================
[15:01] - Upgrading: Default
[15:01] - Database schema mismatch: migration is available.
Do you want to upgrade to new schema? Y(es)/n(o) y
Upgrading schema ...
Done.
Database is OK.
[15:01] - ========================
```

Schema upgrade can be done for multiple products in a row if the
`CodeChecker server --db-upgrade-schema all` command is used. A prompt will ask
for user input for each product, no schema modification is done without asking
the user.
If you want to do the migration without user interaction you can use the
`--db-force-upgrade` option of the server command.

# Further reading

You should also read the [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script)
and the [Operation Reference](https://alembic.sqlalchemy.org/en/latest/ops.html)
for details.

- [Auto Generating Migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Alembic Operation Reference](https://alembic.sqlalchemy.org/en/latest/ops.html)
