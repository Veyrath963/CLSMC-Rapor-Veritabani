def csrf(client, path="/"):
    client.get(path)
    with client.session_transaction() as session:
        return session["_csrf_token"]


def test_post_without_csrf_is_rejected(client):
    response = client.post("/login", data={"username": "x", "password": "y"})
    assert response.status_code == 400


def test_login_form_has_csrf(client):
    response = client.get("/")
    assert b"_csrf_token" in response.data


def test_health_is_available(client):
    response = client.get("/health")
    assert response.status_code == 200
