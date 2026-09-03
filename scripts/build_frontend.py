import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_ROOT / "app"
OUTPUT_DIRECTORY = PROJECT_ROOT / "dist"


def validated_api_base_url() -> str:
    """Return the HTTP(S) API origin required by the static frontend build."""
    value = os.getenv("LINKMINT_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("LINKMINT_API_BASE_URL must be a complete HTTP(S) origin")
    return value


def build_frontend() -> None:
    """Create a clean static frontend configured for the deployed API origin."""
    api_base_url = validated_api_base_url()
    if OUTPUT_DIRECTORY.exists():
        shutil.rmtree(OUTPUT_DIRECTORY)

    output_assets = OUTPUT_DIRECTORY / "assets"
    output_assets.mkdir(parents=True)
    shutil.copytree(SOURCE_DIRECTORY / "static", output_assets, dirs_exist_ok=True)

    template = (SOURCE_DIRECTORY / "templates" / "index.html").read_text(encoding="utf-8")
    static_html = template.replace("__PUBLIC_BASE_URL__", api_base_url)
    static_html = static_html.replace('href="/assets/', 'href="assets/')
    static_html = static_html.replace('src="/assets/', 'src="assets/')
    (OUTPUT_DIRECTORY / "index.html").write_text(static_html, encoding="utf-8")


if __name__ == "__main__":
    build_frontend()

