import pytest
from app.database import db
from app.models.user import User

def test_user_password_hashing(app):
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        assert user.password_hash != "SecurePass123!"
        assert user.check_password("SecurePass123!") is True
        assert user.check_password("WrongPass") is False
        assert user.check_password("") is False

def test_login_page_renders(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Sign In to Account" in response.data
    assert b"demo_user" in response.data

def test_login_successful_with_username(client, app):
    with app.app_context():
        user = User(username="alice", email="alice@example.com")
        user.set_password("MySecretPass123")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/login", data={
        "identifier": "alice",
        "password": "MySecretPass123",
        "remember": "on"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, alice!" in response.data
    assert b"alice" in response.data

def test_login_successful_with_email(client, app):
    with app.app_context():
        user = User(username="bob", email="bob@company.org")
        user.set_password("CompanyPass123")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/login", data={
        "identifier": "bob@company.org",
        "password": "CompanyPass123"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, bob!" in response.data

def test_login_invalid_password(client, app):
    with app.app_context():
        user = User(username="charlie", email="charlie@test.com")
        user.set_password("CorrectPassword")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/login", data={
        "identifier": "charlie",
        "password": "WrongPassword"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid credentials" in response.data

def test_login_nonexistent_user(client):
    response = client.post("/auth/login", data={
        "identifier": "ghost_user",
        "password": "SomePassword"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid credentials" in response.data

def test_login_missing_fields(client):
    response = client.post("/auth/login", data={
        "identifier": "",
        "password": ""
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Please enter both username/email and password" in response.data

def test_register_page_renders(client):
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b"Create Account" in response.data

def test_register_successful(client, app):
    response = client.post("/auth/register", data={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "StrongPassword99",
        "confirm_password": "StrongPassword99"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Account created successfully" in response.data

    with app.app_context():
        user = User.query.filter_by(username="newuser").first()
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.check_password("StrongPassword99") is True

def test_register_password_mismatch(client):
    response = client.post("/auth/register", data={
        "username": "mismatchuser",
        "email": "mismatch@example.com",
        "password": "Password123",
        "confirm_password": "DifferentPassword123"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Passwords do not match" in response.data

def test_register_duplicate_username(client, app):
    with app.app_context():
        user = User(username="existinguser", email="existing@test.com")
        user.set_password("Pass1234")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/register", data={
        "username": "existinguser",
        "email": "different@test.com",
        "password": "Pass123456",
        "confirm_password": "Pass123456"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Username already taken" in response.data

def test_register_duplicate_email(client, app):
    with app.app_context():
        user = User(username="firstuser", email="common@test.com")
        user.set_password("Pass1234")
        db.session.add(user)
        db.session.commit()

    response = client.post("/auth/register", data={
        "username": "seconduser",
        "email": "common@test.com",
        "password": "Pass123456",
        "confirm_password": "Pass123456"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Email is already registered" in response.data

def test_logout(client, app):
    # Register and log in
    client.post("/auth/register", data={
        "username": "logoutuser",
        "email": "logout@test.com",
        "password": "Pass123456",
        "confirm_password": "Pass123456"
    }, follow_redirects=True)

    # Logout
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been signed out." in response.data

def test_unauthenticated_user_redirected_to_login(app):
    app.config["REQUIRE_LOGIN"] = True
    test_client = app.test_client()
    res = test_client.get("/")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]
    app.config["REQUIRE_LOGIN"] = False

