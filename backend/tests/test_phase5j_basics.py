from app.constants.participant_grades import PARTICIPANT_GRADES
from app.constants.study_title import STUDY_PROJECT_TITLE
from app.services.fictional_name_pairs import load_name_pairs, pair_count, select_pairs_deterministic


def test_middle_school_grades_in_catalog():
    for grade in ("6th Grade", "7th Grade", "8th Grade"):
        assert grade in PARTICIPANT_GRADES


def test_fictional_name_pairs_dataset_count():
    assert pair_count() == 50_000


def test_fictional_pairs_have_parent_and_participant():
    pairs = load_name_pairs()
    sample = pairs[0]
    assert sample["participant_name"]
    assert sample["parent_name"]


def test_deterministic_name_pair_selection():
    a = select_pairs_deterministic(batch_key="batch-1", count=3, start_offset=0)
    b = select_pairs_deterministic(batch_key="batch-1", count=3, start_offset=0)
    assert a == b


def test_study_project_title_exact():
    assert "digital biomarkers" in STUDY_PROJECT_TITLE
    assert STUDY_PROJECT_TITLE.startswith("NeuroCortex:")
