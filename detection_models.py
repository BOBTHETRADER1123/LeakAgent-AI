from pydantic import BaseModel, Field, ConfigDict

class DetectionRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    rows: list[dict] = Field(min_length=1, max_length=10000)

class SpatialDetectionRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    rows: list[dict] = Field(min_length=2, max_length=50000)
    pipe_length_m: float | None = Field(default=None, gt=0, le=10000000)
