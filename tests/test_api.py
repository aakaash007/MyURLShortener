import string

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.models import Base, Link
from app.repository import LinkRepository
from app.service import MAX_CODE_ATTEMPTS, CodeGenerationExhausted, create_short_link


def test_create_link_returns_base62_code_and_absolute_url(client: TestClient) -> None:
    """Verify link creation returns a usable seven-character Base62 code."""
    response = client.post(
        "/links",
        json={"target_url": "https://example.com/articles?id=42"},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["short_code"]) == 7
    assert set(body["short_code"]) <= set(string.ascii_letters + string.digits)
    assert body["short_url"] == f"http://testserver/{body['short_code']}"
    assert body["target_url"] == "https://example.com/articles?id=42"


def test_follow_link_returns_temporary_redirect(client: TestClient) -> None:
    """Verify a created code redirects to its exact stored destination."""
    target_url = "https://example.com/path?q=fastapi#section"
    created = client.post("/links", json={"target_url": target_url}).json()

    response = client.get(f"/{created['short_code']}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == target_url


def test_unknown_code_returns_not_found(client: TestClient) -> None:
    """Verify unknown short codes produce a clear 404 response."""
    response = client.get("/notFound", follow_redirects=False)

    assert response.status_code == 404
    assert response.json() == {"detail": "Short link not found"}


@pytest.mark.parametrize(
    "target_url",
    [
        "not-a-url",
        "ftp://example.com/file",
        "https://",
        "https://user:secret@example.com/private",
    ],
)
def test_invalid_or_unsupported_urls_are_rejected(
    client: TestClient,
    target_url: str,
) -> None:
    """Verify malformed and non-HTTP destinations fail validation."""
    response = client.post("/links", json={"target_url": target_url})

    assert response.status_code == 422


def test_links_survive_application_restart(tmp_path, settings: Settings) -> None:
    """Verify SQLAlchemy mappings survive application and engine restarts."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'persistent.db'}"
    first_engine = create_engine(database_url)
    Base.metadata.create_all(first_engine)
    with TestClient(create_app(settings=settings, engine=first_engine)) as first_client:
        created = first_client.post(
            "/links",
            json={"target_url": "https://example.org/persisted"},
        ).json()

    second_engine = create_engine(database_url)
    with TestClient(create_app(settings=settings, engine=second_engine)) as second_client:
        response = second_client.get(
            f"/{created['short_code']}",
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.org/persisted"


def test_collision_is_retried(engine) -> None:
    """Verify a duplicate generated code is replaced by the next candidate."""
    with Session(engine) as session:
        repository = LinkRepository(session)
        repository.insert("AAAAAAA", "https://existing.example")
        candidates = iter(["AAAAAAA", "BBBBBBB"])

        short_code = create_short_link(
            repository,
            "https://new.example",
            lambda: next(candidates),
        )

        assert short_code == "BBBBBBB"
        assert repository.get_target(short_code) == "https://new.example"


def test_repeated_collisions_raise_clear_error(engine) -> None:
    """Verify collision retries stop after the configured safety limit."""
    with Session(engine) as session:
        repository = LinkRepository(session)
        repository.insert("AAAAAAA", "https://existing.example")

        with pytest.raises(CodeGenerationExhausted):
            create_short_link(repository, "https://new.example", lambda: "AAAAAAA")

    assert MAX_CODE_ATTEMPTS == 10


def test_frontend_is_served(client: TestClient) -> None:
    """Verify the browser interface is available from the application root."""
    response = client.get("/")

    assert response.status_code == 200
    assert "LinkMint" in response.text
    assert "shorten-form" in response.text


def test_health_and_readiness_are_available(client: TestClient) -> None:
    """Verify deployment health checks cover both web and database readiness."""
    assert client.get("/health").status_code == 204
    assert client.get("/ready").status_code == 204


def test_public_base_url_overrides_request_host(engine) -> None:
    """Verify generated links use the configured production origin."""
    settings = Settings(
        database_url="sqlite+pysqlite://",
        public_base_url="https://go.example.com",
        environment="testing",
    )
    with TestClient(create_app(settings=settings, engine=engine)) as client:
        response = client.post(
            "/links",
            json={"target_url": "https://example.com/destination"},
        )

    assert response.json()["short_url"].startswith("https://go.example.com/")


def test_inactive_link_is_not_redirected(engine, settings: Settings) -> None:
    """Verify a disabled mapping behaves like an unknown short code."""
    with Session(engine) as session:
        session.add(
            Link(
                short_code="DISABLD",
                target_url="https://example.com",
                is_active=False,
            )
        )
        session.commit()

    with TestClient(create_app(settings=settings, engine=engine)) as client:
        response = client.get("/DISABLD", follow_redirects=False)

    assert response.status_code == 404


def test_creation_rate_limit_returns_retry_guidance(engine) -> None:
    """Verify repeated creation requests receive a standard rate-limit response."""
    settings = Settings(
        database_url="sqlite+pysqlite://",
        environment="testing",
        link_creation_limit=1,
        rate_limit_window_seconds=60,
    )
    with TestClient(create_app(settings=settings, engine=engine)) as client:
        first_response = client.post(
            "/links",
            json={"target_url": "https://example.com/first"},
        )
        blocked_response = client.post(
            "/links",
            json={"target_url": "https://example.com/second"},
        )

    assert first_response.status_code == 201
    assert blocked_response.status_code == 429
    assert int(blocked_response.headers["retry-after"]) >= 1


def test_security_headers_are_attached(client: TestClient) -> None:
    """Verify browser responses include the configured defensive headers."""
    response = client.get("/")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]

