"""Package entrypoint: ``python -m src`` runs the FastMCP server.

Imports ``src.app`` as a normal module (not as ``__main__``) so the tool modules
register on the same FastMCP instance that ``run()`` serves — avoiding the
double-import that ``python -m src.app`` would cause.
"""

from .app import run

if __name__ == "__main__":
    run()
