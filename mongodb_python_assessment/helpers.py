import os
import base64
from typing import Any, Dict, Optional

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Standard placeholder used when a movie poster is missing or invalid.
_PLACEHOLDER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="330">'
    '<rect width="100%" height="100%" fill="#e5e7eb"/>'
    '<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
    'font-family="Arial" font-size="18" fill="#6b7280">No Poster</text>'
    '</svg>'
)
PLACEHOLDER_POSTER = "data:image/svg+xml;base64," + base64.b64encode(_PLACEHOLDER_SVG.encode("utf-8")).decode("ascii")

# -----------------------------
# Mongo helpers (PyMongo)
# -----------------------------

_MONGO_CLIENT: Optional[MongoClient] = None


def get_movies_collection():
    """Return sample_mflix.movies collection (lazy singleton client)."""
    global _MONGO_CLIENT
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MFLIX_DB", "sample_mflix")
    coll_name = os.getenv("MFLIX_COLLECTION", "movies")

    if _MONGO_CLIENT is None:
        # certifi helps when connecting to Atlas from environments missing CA bundle.
        _MONGO_CLIENT = MongoClient(
            uri,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
        )
    return _MONGO_CLIENT[db_name][coll_name]


def serialize_movie(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Make Mongo docs JSON-serializable and UI-friendly."""
    imdb = doc.get("imdb") or {}
    poster = doc.get('poster') or ""
    # Use a standard placeholder if the poster is missing or empty.
    if not poster:
        poster = PLACEHOLDER_POSTER

    return {
        "id": str(doc.get("_id")),
        "title": doc.get("title") or "Untitled",
        "year": doc.get("year"),
        "genres": doc.get("genres") or [],
        "plot": doc.get("plot") or "",
        "runtime": doc.get("runtime"),
        "rated": doc.get("rated"),
        "imdb_rating": imdb.get("rating"),
        "poster": poster,
    }
