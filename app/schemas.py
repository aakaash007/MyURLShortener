from pydantic import BaseModel, HttpUrl, field_validator


class LinkCreate(BaseModel):
    """Validate the HTTP or HTTPS destination supplied by a client."""

    target_url: HttpUrl

    @field_validator("target_url")
    @classmethod
    def reject_embedded_credentials(cls, value: HttpUrl) -> HttpUrl:
        """Reject URLs that could expose embedded usernames or passwords."""
        if value.username or value.password:
            raise ValueError("URLs containing credentials are not allowed")
        return value


class LinkResponse(BaseModel):
    """Describe a newly created shortened link."""

    short_code: str
    short_url: str
    target_url: HttpUrl
