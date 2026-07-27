"""Query -> top-k relevant code chunks for a repo."""

from app.rag import embeddings, vectorstore


async def retrieve(repo_id: str, query: str, k: int = 8) -> list[dict]:
    vector = await embeddings.embed_query(query)
    client = vectorstore.get_client()
    try:
        return await vectorstore.search(client, repo_id, vector, limit=k)
    finally:
        await client.close()
