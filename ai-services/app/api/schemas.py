"""User input constraints for the fixed model's supported domain."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["Nhà ở", "Đất nền", "Căn hộ chung cư"]
Area = Annotated[float, Field(strict=True, ge=20, le=1000, allow_inf_nan=False)]
# 0 is the posting form's "not declared" marker; it normalises to missing before
# inference instead of being fed to the model as a fake bedroom count.
Rooms = Annotated[int, Field(strict=True, ge=0, le=30)]
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
    # Optional real measurements. None means the user does not know; never a default.
    road_width_m: Annotated[float, Field(gt=0, le=100, allow_inf_nan=False)] | None = None
    frontage_width_m: Annotated[float, Field(gt=0, le=500, allow_inf_nan=False)] | None = None
    street_name: Annotated[str, Field(strict=True, max_length=200)] | None = None
    project_name: Annotated[str, Field(strict=True, max_length=200)] | None = None
    bathrooms: Annotated[int, Field(strict=True, ge=1, le=30)] | None = None
    house_direction: Annotated[str, Field(strict=True, max_length=50)] | None = None
    balcony_direction: Annotated[str, Field(strict=True, max_length=50)] | None = None
    road_width_source: Literal["user", "verified"] | None = None
    frontage_width_source: Literal["user", "verified"] | None = None

    @model_validator(mode="after")
    def zero_rooms_means_undeclared(self):
        # Declared 0 means "not declared": drop it so the model keeps its
        # own missing-value handling. 1..30 remain real values.
        if self.rooms == 0:
            self.rooms = None
        return self

    @model_validator(mode="after")
    def applicable_fields(self):
        if self.category == "Đất nền" and self.rooms is not None:
            raise ValueError("Đất nền không nhận số phòng ngủ.")
        if self.category != "Nhà ở" and (self.floors is not None or self.house_subtype is not None):
            raise ValueError("Số tầng nhà và subtype chỉ áp dụng Nhà ở; không dùng tầng tòa/căn hộ.")
        if self.category != "Căn hộ chung cư" and self.balcony_direction is not None:
            raise ValueError("Hướng ban công chỉ áp dụng căn hộ chung cư.")
        if self.category == "Căn hộ chung cư" and self.access_type is not None:
            raise ValueError("Mặt tiền/kiệt không áp dụng cho căn hộ trong model này.")
        if self.category == "Căn hộ chung cư" and (self.road_width_m is not None or self.frontage_width_m is not None):
            raise ValueError("Chiều rộng đường/mặt tiền không áp dụng cho căn hộ trong model này.")
        return self


class UsedFeatures(BaseModel):
    area_sqm: float
    location_feature: str
    ward_source: str | None
    rooms: int | None
    floors: float | None
    access_type: str | None
    house_subtype: str | None


class ShapFactor(BaseModel):
    feature_name: str
    label: str
    shap_value: float
    impact_pct: float
    direction: Literal["increase", "decrease"]
    context_note: str = ""


class ShapExplanation(BaseModel):
    base_value_log: float
    base_price_vnd: int
    scale: str = "log_asking_price"
    top_factors: list[ShapFactor]
    method: str = "TreeSHAP (Native Additive Contribution)"
    summary_vi: str


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
    shap_explanation: ShapExplanation | None = None
    valuation_timestamp: str | None = None


class V1_3PreviewResponse(BaseModel):
    is_preview: bool = True
    model_version: Literal["v1.3"]
    status: str = "PREVIEW_EXPERIMENTAL"
    predicted_asking_price_vnd: int
    predicted_asking_price_billion: float
    price_band: str
    calibration_factor: float
    calibration_policy: str
    naive_price_vnd: int
    features_used: dict
    missing_features: list[str]
    # WP-04 additive explanation object; the legacy shap_explanation above is unchanged.
    explanation: dict | None = None
    # Additive: the caller needs to see when the model could not verify the location.
    warnings: list[str] = []
    shap_explanation: ShapExplanation | None = None
    valuation_timestamp: str
    disclaimer: str
