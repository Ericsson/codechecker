"""Add columns for number of runs and latest run storage

Revision ID: 4db450cf38af
Revises: 7ceea9232211
Create Date: 2021-06-28 15:52:57.237509

"""

# revision identifiers, used by Alembic.
revision = '4db450cf38af'
down_revision = '7ceea9232211'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from codechecker_common.logger import get_logger
from codechecker_server.database import database
from codechecker_server.database.run_db_model import IDENTIFIER as RUN_META
from codechecker_web.shared import webserver_context

LOG = get_logger('system')


def upgrade():
    op.add_column(
        'products',
        sa.Column(
            'latest_storage_date',
            sa.DateTime(),
            nullable=True))

    op.add_column(
        'products',
        sa.Column(
            'num_of_runs',
            sa.Integer(),
            server_default="0",
            nullable=True))

    try:
        product_con = op.get_bind()
        products = product_con.execute(
            "SELECT id, connection from products").fetchall()

        context = webserver_context.get_context()
        for id, connection in products:
            sql_server = database.SQLServer.from_connection_string(
                connection, RUN_META, context.run_migration_root)

            engine = sa.create_engine(sql_server.get_connection_string())
            conn = engine.connect()

            run_info = \
                conn.execute("SELECT count(*), max(date) from runs").fetchone()

            values = [f"num_of_runs={run_info[0]}"]
            if run_info[1]:
                values.append(f"latest_storage_date='{run_info[1]}'")

            product_con.execute(f"""
                UPDATE products
                SET {', '.join(values)}
                WHERE id={id}
            """)
    except Exception as ex:
        LOG.error("Failed to fill product detail columns (num_of_runs, "
                  "latest_storage_date): %s", ex)
        pass

def downgrade():
    op.drop_column('products', 'num_of_runs')
    op.drop_column('products', 'latest_storage_date')
