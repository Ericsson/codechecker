# How to modify the database schema

CodeChecker is developed in rolling release model so it is important to update
the database schema in a backward compatible way. This is achieved using the
[Alembic](http://alembic.readthedocs.org/en/latest/index.html) database
migration tool.

This is a step-by-step guide, how to modify the schema in a backward compatible
way using migration scripts.

## Step 1: Update the database model

CodeChecker uses [SQLAlchemy](http://www.sqlalchemy.org/) for database
operations. You can find the database model in db_model/orm_model.py file. When
you want to modify the database schema you should update this file first.

Please read [SQLAlchemy declarative syntax documentation](http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/)
for syntax and semantics.

## Step 2: Write a migration script

When you change the database schema, it's essential to write a migration script.
When you start CodeChecker with an existing database, it will automatically
migrate the schema to the latest version using Alembic migration scripts.

You can write the migration script manually or you can use Alembic's
'autogenerate' feature.

### Step 2.A: Generating migration scripts using autogenerate

Alembic can compare the table metadata against the status of a database and
based on this comparison it generates the migration script. Even though this
method has it's [limitations](
http://alembic.readthedocs.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect)
, in most cases it works well.

To generate a migration script, do the following steps:
1. Start a database with the original, unmodified schema.
2. Go to CodeChecker's source root
3. Edit the sqlalchemy.url option in [alembic.ini](
   http://alembic.readthedocs.org/en/latest/tutorial.html#editing-the-ini-file)
   according to your database configuration.
4. Generate the migration script using alembic:
   ```
   alembic revision --autogenerate -m "Change description"
   ```
5. The new migration script db_migrate/versions/{hash}_change_description.py is
   generated. **You must always check the generated script because sometimes it
   isn't correct.**
6. Run all test cases. **All unit tests must pass**.
7. Don't forget to commit the migration script with your other changes.

Further reading:
- [Auto Generating Migrations](http://alembic.readthedocs.org/en/latest/autogenerate.html)
- [Alembic tutorial](http://alembic.readthedocs.org/en/latest/tutorial.html)
- [Alembic Operation Reference](http://alembic.readthedocs.org/en/latest/ops.html)

### Step 2.B: Writing migration scripts by hand

Navigate to the root directory of CodeChecker source code and create an empty
migration script using `alembic revision`:

```
alembic revision -m "Change description"
```

The new file db_migrate/versions/{hash}_change_description.py is generated. This
file contains an empty `upgrade` and a `downgrade` function. You should always
implement the `upgrade` function. Downgrading is not supported right now.

You should also read the [Alembic tutorial](http://alembic.readthedocs.org/en/latest/tutorial.html#create-a-migration-script)
and the [Operation Reference](http://alembic.readthedocs.org/en/latest/ops.html)
for details.
