"""Explicit local evidence service; no task starts until a user/browser request."""

import argparse
from pathlib import Path

import uvicorn

from pybert.web.server import create_app
from pybert.web.tasks import Tasks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    uvicorn.run(create_app(Tasks(args.directory)), host="127.0.0.1", port=args.port)
