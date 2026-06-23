from __future__ import annotations

import json
from typing import Any, Iterable


class EmbeddingsMixin:
    def save_embedding(self, user_id: str, embedding: Iterable[float], model_name: str) -> None:
        data = json.dumps([float(x) for x in embedding])
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO face_embeddings(user_id, embedding_data, model_name, created_at) VALUES (?, ?, ?, ?)",
                (user_id, data, model_name, self.now()),
            )
            conn.commit()

    def delete_embeddings(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM face_embeddings WHERE user_id = ?", (user_id,))
            conn.commit()

    def load_active_embeddings(self, model_name: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT e.embedding_id, e.user_id, e.embedding_data, e.model_name, u.full_name, u.role, u.status
            FROM face_embeddings e
            JOIN users u ON u.user_id = e.user_id
            WHERE u.status = 'active'
        """
        params: list[Any] = []
        if model_name:
            query += " AND e.model_name = ?"
            params.append(model_name)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["embedding"] = json.loads(item.pop("embedding_data"))
            result.append(item)
        return result
