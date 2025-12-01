"""Helper template for Alembic migration scripts.
This is a minimal copy of the default template used by Alembic.
"""
<%!
from alembic import op
%>
"""
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

revision = '${up_revision}'
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

% if imports:
${imports}
% endif

def upgrade():
% if upgrades:
    ${upgrades}
% else:
    pass
% endif


def downgrade():
% if downgrades:
    ${downgrades}
% else:
    pass
% endif
