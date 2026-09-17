"""
Tests for Functional Passenger Journey Integration & Authentication Sync (SIH26028).
Verifies:
1. Public train/ticket access when logged out.
2. Sign-in, JWT token creation, and auth persistence.
3. Associating verified PNR/ticket with authenticated user account.
4. Retrieving saved journey across sessions.
5. Clearing saved journey.
"""

import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.routes.auth import create_token
from backend.database import get_user_by_identifier, save_user_journey, get_user_journey, clear_user_journey

client = TestClient(app)


def test_public_access_without_login():
    """Unauthenticated visitors must have full access to ticket verification and trains."""
    # Direct PNR verification should work without auth
    resp = client.get("/api/tickets/8429103847")
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_verified"] is True
    assert data["journey"]["train_number"] == "22436"

    # POST verification should work without auth
    resp_post = client.post("/api/tickets/verify", json={"payload": "2840192841"})
    assert resp_post.status_code == 200
    assert resp_post.json()["match_verified"] is True


def test_authenticated_journey_lifecycle():
    """Test full cycle of saving, retrieving, and clearing passenger journey."""
    # 1. Sign up or login a test passenger
    ident = f"psg_{int(time.time())}@railtrack.in"
    signup_resp = client.post("/api/auth/signup", json={
        "name": "Integration Passenger",
        "identifier": ident,
        "password": "Password123!",
    })
    assert signup_resp.status_code == 201
    auth_data = signup_resp.json()
    token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Initially, user has no saved journey
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["active_journey"] is None

    my_j_resp = client.get("/api/tickets/my-journey", headers=headers)
    assert my_j_resp.status_code == 200
    assert my_j_resp.json()["has_journey"] is False

    # 3. Save a verified journey using PNR 8429103847
    save_resp = client.post("/api/tickets/save-journey", json={
        "pnr": "8429103847"
    }, headers=headers)
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["status"] == "SUCCESS"
    assert save_data["pnr"] == "8429103847"

    # 4. Fetch my-journey endpoint
    get_resp = client.get("/api/tickets/my-journey", headers=headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["has_journey"] is True
    assert get_data["journey"]["pnr"] == "8429103847"
    assert get_data["journey"]["journey"]["train_number"] == "22436"

    # 5. Fetch /api/auth/me and verify active_journey is populated
    me_after = client.get("/api/auth/me", headers=headers)
    assert me_after.status_code == 200
    assert me_after.json()["active_journey"]["pnr"] == "8429103847"

    # 6. Clear saved journey
    del_resp = client.delete("/api/tickets/my-journey", headers=headers)
    assert del_resp.status_code == 200

    # 7. Verify journey is cleared
    check_cleared = client.get("/api/tickets/my-journey", headers=headers)
    assert check_cleared.status_code == 200
    assert check_cleared.json()["has_journey"] is False


def test_save_journey_requires_auth():
    """Attempting to save journey without bearer token must return 401."""
    resp = client.post("/api/tickets/save-journey", json={"pnr": "8429103847"})
    assert resp.status_code == 401
