
from enum import Enum
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator
)


class Tone(str, Enum):
    formal = "Formal"
    professional = "Professional"
    friendly = "Friendly"


class EmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(
        min_length=3,
        max_length=1000
    )
    tone: Tone
    recipient: str = Field(
        min_length=2,
        max_length=100
    )

    @field_validator("purpose", "recipient")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be blank")
        return value


class EmailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)

    @field_validator("subject", "body")
    @classmethod
    def reject_blank_output(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Generated content is empty")
        return value
