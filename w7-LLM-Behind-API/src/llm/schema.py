from enum import Enum
from pydantic import BaseModel, Field


class TriageCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    OTHER = "other"


class TriageUrgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


# Input Schema: Enforces character limits and non-empty strings
class TriageRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Support message to classify (1-2000 characters)"
    )


# Output Schema: The strict contract your endpoint guarantees
class TriageResponse(BaseModel):
    category: TriageCategory
    urgency: TriageUrgency
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., min_length=1)