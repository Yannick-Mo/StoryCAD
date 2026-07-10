import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.knowledge.embeddings import embed_text
from app.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_store = VectorStore(db)

    async def retrieve_context(
        self,
        project_id: uuid.UUID | None,
        genre: str | None,
        query: str,
        limit: int = 5,
    ) -> str:
        chunks = await self.retrieve_chunks(project_id, genre, query, limit)
        if not chunks:
            return ""
        lines = ["## Retrieved Knowledge", ""]
        for i, chunk in enumerate(chunks, 1):
            source = chunk["source_type"].replace("_", " ").title()
            lines.append(f"### {i}. [{source}] {chunk.get('genre', 'General')}")
            if chunk.get("tags"):
                tags = ", ".join(chunk["tags"])
                lines.append(f"**Tags:** {tags}")
            lines.append(chunk["content"])
            lines.append("")
        return "\n".join(lines)

    async def retrieve_chunks(
        self,
        project_id: uuid.UUID | None,
        genre: str | None,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        if settings.embedding_base_url:
            try:
                query_embedding = await embed_text(query)
                return await self.vector_store.search(
                    query_embedding=query_embedding,
                    genre=genre,
                    project_id=project_id,
                    limit=limit,
                )
            except Exception:
                logger.warning("Embedding search failed, falling back to full-text search")
        else:
            logger.info("Embedding not configured, using PostgreSQL full-text search")
        return await self.vector_store.search_fts(
            query=query,
            genre=genre,
            project_id=project_id,
            limit=limit,
        )
