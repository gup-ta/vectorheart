"""Verified scholarly identities, immutable source snapshots and retrieval provenance."""
from alembic import op
from app.literature_models import ScholarlySource, SourceIdentifier, SourceSnapshot, LiteratureHit, ProjectSource, LiteratureCache

revision = '0004'
down_revision = '0003'
MODELS = [ScholarlySource, SourceIdentifier, SourceSnapshot, LiteratureHit, ProjectSource, LiteratureCache]


def upgrade():
    for model in MODELS: model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in reversed(MODELS): model.__table__.drop(op.get_bind())
