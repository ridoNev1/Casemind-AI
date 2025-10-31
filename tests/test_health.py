from app import create_app


def test_health_ping():
    app = create_app("development")
    client = app.test_client()

    response = client.get("/health/ping")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
