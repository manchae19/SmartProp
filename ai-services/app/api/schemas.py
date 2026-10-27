"""User input constraints for the fixed model's supported domain."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["Nhà ở", "Đất nền", "Căn hộ chung cư"]
Area = Annotated[float, Field(strict=True, ge=20, le=1000, allow_inf_nan=False)]
Rooms = Annotated[int, Field(strict=True, ge=1, le=30)]
Floors = Annotated[float, Field(strict=True, ge=1, le=20, allow_inf_nan=False)]


class ValuationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: Category
    area_sqm: Area
    location_feature: Annotated[str, Field(strict=True, min_length=1, max_length=200)]
    ward: Annotated[str, Field(strict=True, max_length=100)] | None = None
    rooms: Rooms | None = None
    floors: Floors | None = None
    access_type: Literal["alley", "frontage"] | None = None
    house_subtype: Literal["villa", "house_c4"] | None = None
    title: Annotated[str, Field(strict=True, max_length=500)] = ""
    description: Annotated[str, Field(strict=True, max_length=8000)] = ""

    @model_validator(mode="after")
    def applicable_fields(self):
        if self.category == "Đất nền" and self.rooms is not None:
            raise ValueError("Đất nền không nhận số phòng ngủ.")
        if self.category != "Nhà ở" and (self.floors is not None or self.house_subtype is not None):
            raise ValueError("Số tầng nhà và subtype chỉ áp dụng Nhà ở; không dùng tầng tòa/căn hộ.")
        if self.category == "Căn hộ chung cư" and self.access_type is not None:
            raise ValueError("Mặt tiền/kiệt không áp dụng cho căn hộ trong model này.")
        return self


class UsedFeatures(BaseModel):
    area_sqm: float
    location_feature: str
    ward_source: str | None
    rooms: int | None
    floors: float | None
    access_type: str | None
    house_subtype: str | None


class PredictionResponse(BaseModel):
    model_version: Literal["v6"]
    model_run: str
    configuration: Literal["all"]
    category: Category
    predicted_asking_price_vnd: int
    predicted_asking_price_million: float
    currency: Literal["VND"]
    price_basis: str
    features_used: UsedFeatures
    missing_features: list[str]
    warnings: list[str]
