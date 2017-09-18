# How to modify the database schema

CodeChecker is developed in rolling release model so it is important to update
the database schema in a backward compatible way. This is achieved using the
[Alembic](http://alembic.readthedocs.org/en/latest/index.html) database
migration tool.

CodeChecker uses [SQLAlchemy](http://www.sqlalchemy.org/) for database
operations. Please read [SQLAlchemy declarative syntax documentation](http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/)
for syntax and semantics.

Alembic can compare the table metadata against the status of a database and
based on this comparison it generates the migration script. Even though this
method has it's [limitations](
http://alembic.readthedocs.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect)
, in most cases it works well.

# Updating configuration database schema

Config database schema scripts can be found under the `config_db_migrate` directory.

## Automatic migration script generation (Online)

A Codechecker server should be started with the previous database schema
version.

### **Step 1**: Update the database model

The configuration database schema file can be found here: `libcodechecker/server/config_db_model.py`

### **Step 2**: Check the alembic.ini configuration settings

Database connection should point to the correct database.
Edit the sqlalchemy.url option in [alembic.ini](
   http://alembic.readthedocs.org/en/latest/tutorial.html#editing-the-ini-file)
   according to your database configuration.

### **Step 3**: Use alembic to autogenerate migration scripts

`alembic --name config_db revision --autogenerate -m "Change description"`

### **Step 4**: Check the generated scripts
The new migration script `config_db_migrate/versions/{hash}_change_description.py` is
   generated. **You must always check the generated script because sometimes it
   isn't correct.**

### **Step 5**: Run all test cases.

**All tests must pass!**

### **Step 6**: Commit the new version files.

Don't forget to commit the migration script with your other changes.


# Updating the run database

## Automatic migration script generation (Online)

A Codechecker server should be started and a product should be configured with a previous database schema version.

### **Step 1**: Update the database model

The run database schema file can be found here: `libcodechecker/server/run_db_model.py`

### **Step 2**: Check alembic.ini configuration

Database connection should point to the correct database.
Edit the sqlalchemy.url option in [alembic.ini](
   http://alembic.readthedocs.org/en/latest/tutorial.html#editing-the-ini-file)
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

The new file `db_migrate/versions/{hash}_change_description.py` is generated. This
file contains an empty `upgrade` and a `downgrade` function.

The empty `upgrade` and `downgrade` should be written by hand.

# Further reading

You should also read the [Alembic tutorial](http://alembic.readthedocs.org/en/latest/tutorial.html#create-a-migration-script)
and the [Operation Reference](http://alembic.readthedocs.org/en/latest/ops.html)
for details.

- [Auto Generating Migrations](http://alembic.readthedocs.org/en/latest/autogenerate.html)
- [Alembic tutorial](http://alembic.readthedocs.org/en/latest/tutorial.html)
- [Alembic Operation Reference](http://alembic.readthedocs.org/en/latest/ops.html)
