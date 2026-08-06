import importlib
import os
import sys

import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    application = module.create_app({"TESTING": True, "WTF_CSRF_ENABLED": True})
    with application.app_context():
        module.db.drop_all()
        module.db.create_all()
        yield application
        module.db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()
