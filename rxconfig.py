import reflex as rx

config = rx.Config(
    app_name="mongodb_python_assessment",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)