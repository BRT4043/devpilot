"""Qdrant operations. One collection for all repos, filtered by repo_id."""

import uuid

from qdrant_client import AsyncQdrantClient, models

from app.config import get_settings

settings = get_settings()

COLLECTION = "devpilot_chunks"


def get_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


async def ensure_collection(client: AsyncQdrantClient, vector_size: int) -> None:
    if await client.collection_exists(COLLECTION):
        return
    await client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    # payload index makes the repo_id filter fast
    await client.create_payload_index(
        collection_name=COLLECTION,
        field_name="repo_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


async def upsert_chunks(
    client: AsyncQdrantClient,
    repo_id: str,
    chunks: list,           # list[Chunk]
    vectors: list[list[float]],
) -> None:
    points = [
        models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "repo_id": repo_id,
                "file_path": c.file_path,
                "language": c.language,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "text": c.text,
            },
        )
        for c, vec in zip(chunks, vectors)
    ]
    # upsert in slices to keep request sizes sane
    for i in range(0, len(points), 128):
        await client.upsert(collection_name=COLLECTION, points=points[i : i + 128])


async def delete_repo_vectors(client: AsyncQdrantClient, repo_id: str) -> None:
    if not await client.collection_exists(COLLECTION):
        return
    await client.delete(
        collection_name=COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
            )
        ),
    )


async def get_by_file(
    client: AsyncQdrantClient,
    repo_id: str,
    file_path: str,
    limit: int = 50,
) -> list[dict]:
    """All indexed chunks for one exact file, in file order. Used when we already know
    which file matters (e.g. a path pulled out of a stack trace) rather than searching."""
    points, _ = await client.scroll(
        collection_name=COLLECTION,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id)),
                models.FieldCondition(key="file_path", match=models.MatchValue(value=file_path)),
            ]
        ),
        limit=limit,
        with_payload=True,
    )
    chunks = [
        {
            "file_path": p.payload["file_path"],
            "start_line": p.payload["start_line"],
            "end_line": p.payload["end_line"],
            "language": p.payload["language"],
            "text": p.payload["text"],
        }
        for p in points
    ]
    return sorted(chunks, key=lambda c: c["start_line"])


async def search(
    client: AsyncQdrantClient,
    repo_id: str,
    query_vector: list[float],
    limit: int = 8,
) -> list[dict]:
    res = await client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        query_filter=models.Filter(
            must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
        ),
        limit=limit,
        with_payload=True,
    )
    return [
        {
            "score": p.score,
            "file_path": p.payload["file_path"],
            "start_line": p.payload["start_line"],
            "end_line": p.payload["end_line"],
            "language": p.payload["language"],
            "text": p.payload["text"],
        }
        for p in res.points
    ]
