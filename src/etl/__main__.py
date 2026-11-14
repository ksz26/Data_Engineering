"""Позволяет запускать пакет как ``python -m etl``."""

import sys

from etl.main import main

sys.exit(main())
