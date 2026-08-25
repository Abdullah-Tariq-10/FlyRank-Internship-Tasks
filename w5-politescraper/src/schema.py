from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

class BookRecord(BaseModel):
    title: str = Field(..., min_length=1)
    product_url: HttpUrl
    price_text: str = Field(..., min_length=1)
    price_gbp: float = Field(..., ge=0.0)
    availability_text: str = Field(..., min_length=1)
    rating_text: str = Field(..., min_length=1)
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str = Field(..., min_length=1)

