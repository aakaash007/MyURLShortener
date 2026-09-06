import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, load_settings
from app.database import Database
from app.rate_limit import SlidingWindowRateLimiter
from app.repository import LinkRepository
from app.schemas import LinkCreate, LinkResponse
from app.service import CodeGenerationExhausted, create_short_link

PACKAGE_DIRECTORY = Path(__file__).parent
LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    """Build the URL shortener with injectable settings and database engine."""
    selected_settings = settings or load_settings()
    database = Database(selected_settings.database_url, engine=engine)
    creation_limiter = SlidingWindowRateLimiter(
        limit=selected_settings.link_creation_limit,
        window_seconds=selected_settings.rate_limit_window_seconds,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Expose shared resources and release database connections on shutdown."""
        application.state.database = database
        yield
        database.dispose()

    application = FastAPI(
        title="LinkMint URL Shortener",
        version="0.2.0",
        lifespan=lifespan,
    )
    application.state.database = database
    application.mount(
        "/assets",
        StaticFiles(directory=PACKAGE_DIRECTORY / "static"),
        name="assets",
    )

    if selected_settings.allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=selected_settings.allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    @application.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        """Attach conservative browser security headers to every response."""
        response = await call_next(request)
        if request.url.path in {"/docs", "/redoc"}:
            # FastAPI's documentation UI loads its own bundled assets from jsDelivr.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "base-uri 'self'; frame-ancestors 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "style-src 'self' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; "
                "script-src 'self'; connect-src 'self'; "
                "img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'"
            )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @application.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, error: SQLAlchemyError) -> Response:
        """Return a stable response when PostgreSQL is temporarily unavailable."""
        LOGGER.error("Database operation failed for %s", request.url.path, exc_info=error)
        return JSONResponse(
            content={"detail": "Database is unavailable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def get_session() -> Iterator[Session]:
        """Provide one SQLAlchemy session to an API request."""
        yield from database.sessions()

    def enforce_creation_limit(request: Request) -> None:
        """Reject clients that exceed the configured link-creation rate."""
        client_key = request.client.host if request.client else "unknown"
        allowed, retry_after = creation_limiter.check(client_key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many links created; try again shortly",
                headers={"Retry-After": str(retry_after)},
            )

    SessionDependency = Annotated[Session, Depends(get_session)]

    @application.get(
        "/",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    def frontend(request: Request) -> HTMLResponse:
        """Serve the browser interface with a trusted API and sharing origin."""
        base_url = str(selected_settings.public_base_url or request.base_url).rstrip("/")
        template = (PACKAGE_DIRECTORY / "templates" / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(template.replace("__PUBLIC_BASE_URL__", base_url))

    @application.get(
        "/favicon.ico",
        response_class=FileResponse,
        include_in_schema=False,
    )
    def favicon() -> FileResponse:
        """Serve the brand icon requested automatically by browsers."""
        return FileResponse(
            PACKAGE_DIRECTORY / "static" / "favicon.svg",
            media_type="image/svg+xml",
        )

    @application.get("/health", status_code=status.HTTP_204_NO_CONTENT)
    def health() -> Response:
        """Confirm that the web process is running."""
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.get("/ready", status_code=status.HTTP_204_NO_CONTENT)
    def readiness() -> Response:
        """Confirm that the application can reach PostgreSQL."""
        try:
            database.is_ready()
        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is unavailable",
            ) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @application.post(
        "/links",
        response_model=LinkResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a shortened link",
    )
    def create_link(
        payload: LinkCreate,
        request: Request,
        session: SessionDependency,
        _: Annotated[None, Depends(enforce_creation_limit)],
    ) -> LinkResponse:
        """Create and return a durable shortened link for a validated URL."""
        repository = LinkRepository(session)
        try:
            short_code = create_short_link(repository, str(payload.target_url))
        except CodeGenerationExhausted as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not allocate a unique short code",
            ) from error

        base_url = str(selected_settings.public_base_url or request.base_url).rstrip("/")
        return LinkResponse(
            short_code=short_code,
            short_url=f"{base_url}/{short_code}",
            target_url=payload.target_url,
        )

    @application.get(
        "/{short_code}",
        response_class=RedirectResponse,
        status_code=status.HTTP_302_FOUND,
        summary="Follow a shortened link",
    )
    def follow_link(short_code: str, session: SessionDependency) -> RedirectResponse:
        """Redirect a known short code to its stored destination with HTTP 302."""
        target_url = LinkRepository(session).get_target(short_code)
        if target_url is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Short link not found",
            )
        return RedirectResponse(target_url, status_code=status.HTTP_302_FOUND)

    return application


app = create_app()
