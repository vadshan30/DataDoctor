from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_app_creation():
    assert app is not None
    assert app.title == "DataDoctor"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["app_name"] == "DataDoctor"
    assert "version" in data
    assert "environment" in data


def test_openapi_schema():
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema


def test_auth_register_and_login():
    response = client.post(
        "/api/v1/auth/register",
        params={"email": "test@example.com", "password": "secret123", "full_name": "Test User"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

    response = client.post(
        "/api/v1/auth/login",
        params={"email": "test@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_login_invalid():
    response = client.post(
        "/api/v1/auth/login",
        params={"email": "nope@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_models_import():
    from app.models import Dataset, Experiment, Report, TrainedModel, User

    assert User is not None
    assert Dataset is not None
    assert Experiment is not None
    assert TrainedModel is not None
    assert Report is not None


def test_config_loads():
    from app.core.config import settings

    assert settings.APP_NAME == "DataDoctor"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.JWT_ALGORITHM == "HS256"


def test_security_roundtrip():
    from app.core.security import create_access_token, decode_access_token, hash_password, verify_password

    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrong", hashed)

    token = create_access_token(subject=1)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
