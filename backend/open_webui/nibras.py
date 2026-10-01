"""
NIBRAS Configuration Abstraction for OFPPT
Provides environment variable handling and defaults for the NIBRAS institutional version.
"""

import os
import logging

log = logging.getLogger(__name__)

# Institutional Branding & App Name
NIBRAS_APP_NAME = os.getenv('NIBRAS_APP_NAME', 'Chat NIBRAS')

# Default LLM Model configured via deployment environment (e.g. qwen3:8b, qwen3:14b, etc.)
NIBRAS_DEFAULT_MODEL = os.getenv('NIBRAS_DEFAULT_MODEL', '').strip()

# Theme & Palette Tokens (OFPPT identity)
NIBRAS_PRIMARY_COLOR = os.getenv('NIBRAS_PRIMARY_COLOR', '#0066B0')
NIBRAS_SECONDARY_COLOR = os.getenv('NIBRAS_SECONDARY_COLOR', '#0C8447')
NIBRAS_ACCENT_COLOR = os.getenv('NIBRAS_ACCENT_COLOR', '#0C8447')


def get_nibras_default_model(fallback=None):
    """
    Returns the NIBRAS configured default model if specified in the environment,
    otherwise returns the fallback value.
    """
    if NIBRAS_DEFAULT_MODEL:
        return NIBRAS_DEFAULT_MODEL
    return fallback
