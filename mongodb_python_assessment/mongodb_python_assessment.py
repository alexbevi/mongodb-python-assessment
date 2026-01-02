from typing import Any, Dict

import reflex as rx
from .state import MovieState
from .helpers import PLACEHOLDER_POSTER

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
