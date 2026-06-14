"""Entry point for Streamlit Cloud deployment."""
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "cli_python"))

import dashboard  # noqa: F401 — triggers streamlit app at module level
