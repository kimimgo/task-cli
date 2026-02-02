"""Entry point for task-cli when run as a module.

This allows the package to be run with: python -m src
"""

import sys

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
