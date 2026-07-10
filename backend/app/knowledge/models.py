import uuid
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.project.models import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    source_type = Column(String(50), nullable=False)
    genre = Column(String(100), nullable=True)
    tags = Column(ARRAY(String), default=[])
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class SkillDefinition(Base):
    __tablename__ = "skill_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    genre = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    config = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class ProjectSkill(Base):
    __tablename__ = "project_skills"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    skill_name = Column(String(100), ForeignKey("skill_definitions.name", ondelete="CASCADE"), primary_key=True)
    config_override = Column(JSONB, default={})
    sort_order = Column(Integer, default=0)
