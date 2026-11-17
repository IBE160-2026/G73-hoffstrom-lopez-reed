"""Inngangspunktet for appen i produksjon (Vercel, E0-S21).

``app`` bygges med ``create_app()``, den samme fabrikken som ``flask --app app run`` finner lokalt, og uten
konfigurasjon, så appen oppfører seg likt lokalt og på Vercel. Vercel finner variabelen via
``[tool.vercel] entrypoint = "wsgi:app"`` i ``pyproject.toml``.

Appen skriver ingenting til disk når den kjører (Vercel har et skrivebeskyttet filsystem). Se arkitektur §11.

Lokalt gir ``flask --app wsgi run --port 8000`` nøyaktig dette objektet.
"""
from app import create_app

app = create_app()
