"""Health endpoint smoke tests."""


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db"] == "ok"
    assert isinstance(payload["ai_chain"], list)
    assert len(payload["ai_chain"]) >= 1


def test_models_metadata_registers_tables():
    from app.db import Base
    from app import models  # noqa: F401

    table_names = set(Base.metadata.tables.keys())
    assert {"sites", "observations", "reviews"} <= table_names
