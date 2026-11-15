from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base, uid, now

class ResearchConversation(Base):
    __tablename__='research_conversations'
    id:Mapped[str]=mapped_column(primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),unique=True)
    created_at:Mapped[str]=mapped_column(default=now)
    updated_at:Mapped[str]=mapped_column(default=now)

class ResearchMessage(Base):
    __tablename__='research_messages'
    id:Mapped[str]=mapped_column(primary_key=True,default=uid)
    conversation_id:Mapped[str]=mapped_column(ForeignKey('research_conversations.id'),index=True)
    role:Mapped[str]
    content:Mapped[str]
    mode:Mapped[str]
    provenance:Mapped[dict]=mapped_column(JSON,default=dict)
    context:Mapped[dict]=mapped_column(JSON,default=dict)
    response_details:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[str]=mapped_column(default=now)
    status:Mapped[str]
    request_key:Mapped[str]
    request_hash:Mapped[str]
    __table_args__=(UniqueConstraint('conversation_id','request_key','role'),)

class ResearchProposal(Base):
    __tablename__='research_proposals'
    id:Mapped[str]=mapped_column(primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    source_message_id:Mapped[str]=mapped_column(ForeignKey('research_messages.id'))
    action_type:Mapped[str]
    payload:Mapped[dict]=mapped_column(JSON)
    source_references:Mapped[list]=mapped_column(JSON)
    provenance:Mapped[dict]=mapped_column(JSON)
    status:Mapped[str]=mapped_column(default='pending')
    result_ids:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[str]=mapped_column(default=now)
    updated_at:Mapped[str]=mapped_column(default=now)
