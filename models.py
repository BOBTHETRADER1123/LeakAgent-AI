from pydantic import BaseModel, Field, ConfigDict

class Reading(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    branch_id: str = Field(min_length=1)
    cycle_id: str = Field(min_length=1)
    q_up_l_s: float = Field(ge=0)
    q_down_l_s: float = Field(ge=0)
    p_up_kpa: float = Field(ge=0)
    p_down_kpa: float = Field(ge=0)
    pipe_storage_change_l_s: float = 0
    branch_tap_l_s: float = Field(default=0,ge=0)
    full_pipe_flag: bool
    stable_window_verified: bool = False
    meter_up_sigma_l_s: float = Field(gt=0)
    meter_down_sigma_l_s: float = Field(gt=0)

class DiagnosisRequest(BaseModel):
    readings: list[Reading] = Field(min_length=1,max_length=2000)
