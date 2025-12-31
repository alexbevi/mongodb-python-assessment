import os
import math
import re
from typing import Any, Dict, List, Optional

import certifi
import base64
import reflex as rx
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


# -----------------------------
# Reflex State
# -----------------------------

class MovieState(rx.State):
    # UI state
    view_mode: str = "cards"
    page_size: str = "25"
    page: int = 0                    # 0-based page index

    # Filters
    q: str = ""
    genre: str = "All"
    min_year: str = ""
    max_year: str = ""

    # Data
    total: int = 0
    movies: List[Dict[str, Any]] = []
    # Misc
    genres: List[str] = ["All"]
    loading: bool = False
    error: str = ""

    # -----------------------------
    # Computed vars
    # -----------------------------

    @rx.var
    def total_pages(self) -> int:
        try:
            page_size_int = int(self.page_size)
        except Exception:
            page_size_int = 25
        if page_size_int <= 0:
            return 1
        return max(1, math.ceil(self.total / page_size_int))

    @rx.var
    def has_prev(self) -> bool:
        return self.page > 0

    @rx.var
    def has_next(self) -> bool:
        try:
            page_size_int = int(self.page_size)
        except Exception:
            page_size_int = 25
        return (self.page + 1) * page_size_int < self.total

    @rx.var
    def page_label(self) -> str:
        return f"Page {self.page + 1} / {self.total_pages}  •  {self.total:,} results"

    # -----------------------------
    # Query builder
    # -----------------------------

    def _criteria(self) -> Dict[str, Any]:
        and_terms: List[Dict[str, Any]] = []

        if self.q.strip():
            # Simple title/plot substring match (demo-friendly).
            # If you want production-grade search, consider Atlas Search indexes.
            safe = re.escape(self.q.strip())
            and_terms.append(
                {
                    "$or": [
                        {"title": {"$regex": safe, "$options": "i"}},
                        {"plot": {"$regex": safe, "$options": "i"}},
                    ]
                }
            )

        if self.genre and self.genre != "All":
            and_terms.append({"genres": self.genre})

        # Year bounds (stored as number in many docs, but keep defensive parsing)
        year_filter: Dict[str, Any] = {}
        if self.min_year.strip().isdigit():
            year_filter["$gte"] = int(self.min_year.strip())
        if self.max_year.strip().isdigit():
            year_filter["$lte"] = int(self.max_year.strip())
        if year_filter:
            and_terms.append({"year": year_filter})

        return {"$and": and_terms} if and_terms else {}

    # -----------------------------
    # Events: filter + paging controls
    # -----------------------------

    def set_query(self, value: str):
        self.q = value

    def set_genre(self, value: str):
        self.genre = value

    def set_min_year(self, value: str):
        self.min_year = value

    def set_max_year(self, value: str):
        self.max_year = value

    # view switching removed; only 'cards' is supported

    def change_page_size(self, value: str):
        try:
            # Keep page_size as a string for Select binding, but validate it's numeric
            self.page_size = str(int(value))
        except Exception:
            self.page_size = "25"
        self.page = 0
        self.movies = []
        self.error = ""
        return MovieState.load_movies

    def apply_filters(self):
        self.page = 0
        self.movies = []
        self.error = ""
        return MovieState.load_movies

    def prev_page(self):
        if self.page <= 0:
            return
        self.page -= 1
        self.movies = []
        return MovieState.load_movies

    def next_page(self):
        if not self.has_next:
            return
        self.page += 1
        self.movies = []
        return MovieState.load_movies

    # -----------------------------
    # Data loaders (background)
    # -----------------------------

    @rx.event(background=True)
    async def load_movies(self):
        """Load current page (and preload next page if in coverflow mode)."""
        try:
            coll = get_movies_collection()
            criteria = self._criteria()
            projection = {
                "title": 1,
                "year": 1,
                "genres": 1,
                "plot": 1,
                "runtime": 1,
                "rated": 1,
                "imdb.rating": 1,
                "poster": 1,
            }

            # Lazily fetch genres once (distinct over array field).
            if len(self.genres) <= 1:
                distinct_genres = sorted([g for g in coll.distinct("genres") if isinstance(g, str)])
                async with self:
                    self.genres = ["All"] + distinct_genres

            async with self:
                self.loading = True
                self.error = ""

            total = coll.count_documents(criteria)
            try:
                page_size_int = int(self.page_size)
            except Exception:
                page_size_int = 25
            skip = self.page * page_size_int

            docs = list(
                coll.find(criteria, projection)
                .sort("title", 1)
                .skip(skip)
                .limit(page_size_int)
            )
            serialized = [serialize_movie(d) for d in docs]

            async with self:
                self.total = total
                self.movies = serialized[: page_size_int]
                self.loading = False

        except Exception as e:
            async with self:
                self.loading = False
                self.error = f"{type(e).__name__}: {e}"

    # prefetch_next_coverflow removed (coverflow disabled)


# -----------------------------
# UI Components
# -----------------------------

def toolbar() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Mflix Movie Browser", size="7"),
                spacing="4",
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.flex(
                rx.input(
                    placeholder="Search title or plot…",
                    value=MovieState.q,
                    on_change=MovieState.set_query,
                    width=["100%", "340px"],
                ),
                rx.select(
                    MovieState.genres,
                    value=MovieState.genre,
                    on_change=MovieState.set_genre,
                    width=["100%", "220px"],
                ),
                rx.input(
                    placeholder="Min year",
                    value=MovieState.min_year,
                    on_change=MovieState.set_min_year,
                    width="120px",
                ),
                rx.input(
                    placeholder="Max year",
                    value=MovieState.max_year,
                    on_change=MovieState.set_max_year,
                    width="120px",
                ),
                rx.select(
                    ["10", "25", "50", "100"],
                    value=MovieState.page_size,
                    on_change=MovieState.change_page_size,
                    width="120px",
                ),
                rx.button("Search", on_click=MovieState.apply_filters),
                rx.spacer(),
                rx.divider(),
                pager(),
                wrap="wrap",
                spacing="3",
                width="100%",
            ),
            rx.cond(
                MovieState.error != "",
                rx.callout(
                    MovieState.error,
                    icon="triangle_alert",
                    color_scheme="red",
                    variant="soft",
                ),
                rx.fragment(),
            ),
            width="100%",
            spacing="4",
        ),
        width="100%",
    )


def movie_card(movie: rx.Var[Dict[str, Any]]) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.image(
                src=movie["poster"],
                width="100%",
                height="260px",
                object_fit="cover",
                alt=movie.get("title", "poster"),
                onerror=f"this.onerror=null;this.src='{PLACEHOLDER_POSTER}';",
            ),
            rx.hstack(
                rx.heading(movie["title"], size="4"),
                rx.spacer(),
                rx.badge(rx.cond(movie["year"], movie["year"], "—")),
                width="100%",
                align="center",
            ),
            rx.text(
                rx.cond(movie["plot"], movie["plot"], "No plot available."),
                size="2",
                max_height="4.5em",
                overflow="hidden",
            ),
            rx.hstack(
                rx.badge(rx.cond(movie["imdb_rating"], rx.text(movie["imdb_rating"]), "n/a")),
                rx.text("IMDb", size="1", color_scheme="gray"),
                rx.spacer(),
                rx.text(movie["genres"], size="1", color_scheme="gray"),
                width="100%",
                align="center",
            ),
            spacing="2",
            width="100%",
        ),
        style={"min_height": "420px"},
    )


def cards_view() -> rx.Component:
    return rx.vstack(
        rx.cond(
            MovieState.loading,
            rx.center(rx.spinner(size="3"), padding_y="6"),
            rx.grid(
                rx.foreach(MovieState.movies, movie_card),
                columns="repeat(4, minmax(0, 1fr))",
                spacing="4",
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
        align="center",
    )


# coverflow UI removed; only cards view is supported


def pager() -> rx.Component:
    next_handler = MovieState.next_page
    prev_handler = MovieState.prev_page

    return rx.hstack(
        rx.button("Prev", on_click=prev_handler, disabled=~MovieState.has_prev),
        rx.text(MovieState.page_label, size="2", color_scheme="gray"),
        rx.button("Next", on_click=next_handler, disabled=~MovieState.has_next),
        width="100%",
        align="center",
        justify="center",
        spacing="4",
        padding_y="2",
    )


def index() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                toolbar(),
                cards_view(),
                spacing="5",
                width="100%",
                align="center",
            )
        ),
        max_width="1200px",
        padding_y="6",
        height="100vh",
        display="flex",
        align="center",
        justify="center",
    )


# App entry
app = rx.App()
app.add_page(index, route="/", on_load=MovieState.load_movies)
