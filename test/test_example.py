# from fastapi.testclient import TestClient
# from app import app

# client = TestClient(app)

# def test_root():
#     response = client.get("/")
#     assert response.status_code == 200
#     assert response.json() == {"message": "Hello from Tim!"}

def test_check():
    print("Hello")
    assert 3 == 3