import secrets
import string
from collections.abc import Callable

from app.repository import LinkRepository

BASE62_ALPHABET = string.ascii_letters + string.digits
DEFAULT_CODE_LENGTH = 7
MAX_CODE_ATTEMPTS = 10


class CodeGenerationExhausted(Exception):
    """Signal that every generated code collided with an existing link."""


def generate_short_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """Generate a cryptographically secure Base62 short code."""
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))


def create_short_link(
    repository: LinkRepository,
    target_url: str,
    code_factory: Callable[[], str] = generate_short_code,
) -> str:
    """Persist a link under the first generated code that does not collide."""
    for _ in range(MAX_CODE_ATTEMPTS):
        short_code = code_factory()
        if repository.insert(short_code, target_url):
            return short_code
    raise CodeGenerationExhausted

