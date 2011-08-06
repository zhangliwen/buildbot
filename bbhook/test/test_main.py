from bbhook.main import app
from bbhook import hook

def test_get():
    client = app.test_client()
    response = client.get('/')


def test_post(monkeypatch):
    client = app.test_client()
    def handle(payload, test):
        assert payload=={}
        assert test==app.config['TESTING']
    monkeypatch.setattr(hook, 'handle', handle)

    app.config['TESTING'] = True
    response = client.post('/', data={'payload':"{}"})

    app.config['TESTING'] = False
    response = client.post('/', data={'payload':"{}"})

    assert response.status_code == 200

def test_post_error(monkeypatch):
    client = app.test_client()
    def handle(payload, test):
        raise Exception('omg')
    monkeypatch.setattr(hook, 'handle', handle)
    response = client.post('/', data={'payload':"{}"})
    assert response.status_code == 500


