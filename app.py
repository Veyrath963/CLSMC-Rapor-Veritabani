from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

# EXAMPLE ONLY — do not put your real Neon password in GitHub.
# On Render, set DATABASE_URL in Dashboard > Service > Environment.

# Render generates SECRET_KEY from render.yaml in production.
SECRET_KEY=change-me-for-local-development
