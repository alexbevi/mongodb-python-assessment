import math
import re
from typing import Any, Dict, List, Optional

import reflex as rx

from .helpers import get_movies_collection, serialize_movie


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
    # Modal state
    modal_open: bool = False
    selected_movie: Optional[Dict[str, Any]] = None

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

    def change_page_size(self, value: str):
        try:
            self.page_size = str(int(value))
        except Exception:
            self.page_size = "25"
        self.page = 0
        self.movies = []
        self.error = ""
        return MovieState.load_movies

    def open_movie(self, movie: Dict[str, Any]):
        self.selected_movie = movie
        self.modal_open = True

    def close_modal(self):
        self.modal_open = False
        self.selected_movie = None

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
