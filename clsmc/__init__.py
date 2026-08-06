"""CLSMC V26 modular service package.

The legacy route surface remains compatible while security, patient and audit
logic are isolated into testable modules.
"""

def create_app(config_overrides=None):
    from app import app
    if config_overrides:
        app.config.update(config_overrides)
    return app
