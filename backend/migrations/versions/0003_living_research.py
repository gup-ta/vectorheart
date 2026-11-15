"""Add graph review, interpretive corrections and bounded investigation checkpoints."""
from alembic import op
from app.stage3_models import ResearchRun, ResearchStep, GraphCorrection

revision = '0003'
down_revision = '0002'


def upgrade():
    for model in [ResearchRun, ResearchStep, GraphCorrection]:
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in [GraphCorrection, ResearchStep, ResearchRun]:
        model.__table__.drop(op.get_bind())
