from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    landId: str | None = Field(default=None, pattern=r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    propertyId: str | None = Field(default=None, pattern=r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
    question: str = Field(min_length=1, max_length=2000)
    budgetVnd: Decimal | None = Field(default=None, ge=1, le=999999999999999, allow_inf_nan=False)
    minPriceVnd: Decimal | None = Field(default=None, ge=1, le=999999999999999, allow_inf_nan=False)
    purpose: Literal["LIVING", "INVESTMENT", "RENTAL"] = "LIVING"
    propertyType: Literal["ALL", "HOUSE", "APARTMENT", "LAND", "VILLA", "ROOM", "COMMERCIAL"] = "ALL"
    minAreaSqm: Decimal | None = Field(default=None, gt=0, le=1000000, allow_inf_nan=False)
    maxAreaSqm: Decimal | None = Field(default=None, gt=0, le=1000000, allow_inf_nan=False)
    minAreaExclusive: bool | None = None
    maxAreaExclusive: bool | None = None
    district: str | None = Field(default=None, min_length=1, max_length=100)
    ward: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=10, strict=True)
    requireGeneration: bool = False
    # Opaque server-issued conversation handle. It carries NO authority and NO facts;
    # it names temporary public context or a durable account-owned conversation.
    # The authenticated API enforces ownership. A public caller can never read a
    # research session because the store is namespaced by authenticated scope.
    sessionId: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    # Public listing the user is currently asking about. The server re-reads it through
    # the public API on every turn, so a draft or private listing can never be addressed.
    propertyId: str | None = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")

    @model_validator(mode="after")
    def ranges_valid(self):
        if self.minPriceVnd is not None and self.budgetVnd is not None and self.minPriceVnd > self.budgetVnd:
            raise ValueError("Minimum price must not exceed budget")
        if self.minAreaSqm is not None and self.maxAreaSqm is not None:
            if self.minAreaSqm > self.maxAreaSqm or (
                self.minAreaSqm == self.maxAreaSqm and (self.minAreaExclusive or self.maxAreaExclusive)
            ):
                raise ValueError("Area range must contain at least one value")
        if (self.minAreaExclusive and self.minAreaSqm is None) or (self.maxAreaExclusive and self.maxAreaSqm is None):
            raise ValueError("An exclusive area bound requires its area")
        return self


class Citation(BaseModel):
    sourceId: str
    url: str
    version: str
    contentHash: str
    scope: Literal["PUBLIC", "INTERNAL_RESEARCH"]
    kind: str
    title: str


class ChatResponse(BaseModel):
    answer: str
    mode: Literal["SAFE", "INTERNAL_RESEARCH"]
    generationMode: Literal["EVIDENCE_ONLY", "QWEN_GROUNDED_PLAN", "QWEN_GROUNDED_ANSWER"]
    retrievalMode: Literal["TOOL_EVIDENCE_ONLY", "E5_FAISS"]
    citations: list[Citation]
    recommendedProperties: list[dict[str, Any]]
    evidence: dict[str, Any]
    dataLimitations: list[str]
