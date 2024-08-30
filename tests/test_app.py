from http import HTTPStatus

from fastapi.testclient import TestClient

from lab import app


def test_home():
    client = TestClient(app)

    response = client.get('/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'lab | em funcionamento'}
