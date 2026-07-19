from pydantic import BaseModel


class StudyConfigResponse(BaseModel):
    study_mode: str
    show_test_data: bool
    allow_participant_predictions: bool
    show_experimental_banner: bool
    block_synthetic_prefixes: list[str]
    synthetic_dataset_prefix: str
    filter_synthetic_data: bool
