import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["STEAM_HUNTER_DB_DIR"] = "/tmp"
os.environ["STEAM_HUNTER_TEST"] = "1"

from app.database import Base, get_db, DATABASE_URL, FoundCode, ASFConfig, NotificationConfig
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    session = TestSession()
    asf_cfg = ASFConfig(ipc_url="http://localhost:1242", ipc_password="", default_bot="principal", auto_redeem=False)
    session.add(asf_cfg)
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_code(db):
    code = FoundCode(
        code="ABCDE-12345-FGHIJ",
        code_type="key",
        source="test/test_source",
        source_url="https://example.com/giveaway",
        title="Test Game",
        status="new",
    )
    db.add(code)
    db.commit()
    return code


@pytest.fixture
def sample_giveaway(db):
    code = FoundCode(
        code="https://store.steampowered.com/app/12345/Test_Game/",
        code_type="giveaway",
        source="test/giveaway_source",
        source_url="https://store.steampowered.com/app/12345/Test_Game/",
        title="Test Free Game",
        status="new",
    )
    db.add(code)
    db.commit()
    return code


@pytest.fixture
def redeemed_code(db):
    code = FoundCode(
        code="XXXXX-YYYYY-ZZZZZ",
        code_type="key",
        source="test/another_source",
        title="Redeemed Game",
        status="redeemed",
    )
    db.add(code)
    db.commit()
    return code
