"""Flask-appen for ankomstprediksjon i Bergen Havn (arkitektur A1, §5)."""
from flask import Flask


def create_app(config=None):
    """Lag appen. Leser ingen .env. Appen skal starte uten (NFR1, NFR6)."""
    app = Flask(__name__)
    if config:
        app.config.update(config)

    @app.get("/")
    def forside():
        # Plassholder til hovedskjermen kommer i E1-S06.
        return (
            '<!doctype html><html lang="nb"><head><meta charset="utf-8">'
            "<title>Ankomstprediksjon · Bergen Havn</title></head>"
            "<body><main><h1>Anløp de neste 24 timene</h1></main></body></html>"
        )

    return app
