"""Add conversation memory and proposal review; preserve existing scientific tables."""
from alembic import op
from app.intelligence_models import ResearchConversation, ResearchMessage, ResearchProposal
revision='0002'
down_revision='0001'
def upgrade():
    for model in [ResearchConversation,ResearchMessage,ResearchProposal]:model.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():
    for model in [ResearchProposal,ResearchMessage,ResearchConversation]:model.__table__.drop(op.get_bind())
