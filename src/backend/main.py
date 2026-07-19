"""ASGI entrypoint that loads env, initializes observability, and exposes create_app()."""

from dotenv import load_dotenv

from agents.observability import initialize_observability
from backend.api import create_app

load_dotenv()
initialize_observability()

app = create_app()
