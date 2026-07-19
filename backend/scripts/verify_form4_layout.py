"""Development-only visual verification for official Form 4 overlay alignment."""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.models.form4_record import Form4Record
from app.services.pdf_form_service import (
    COORDINATES_FILE,
    METADATA_FILE,
    TEMPLATE_PDF,
    compute_template_sha256,
    generate_form4_pdf,
    load_template_metadata,
)

OUTPUT_ROOT = ROOT / "generated_documents" / "form4-verification"


@dataclass
class VerificationCase:
    slug: str
    description: str
    record: Form4Record


def _record(**kwargs) -> Form4Record:
    return Form4Record(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        signer_records=kwargs.pop("signer_records", []),
        **kwargs,
    )


def build_cases() -> list[VerificationCase]:
    return [
        VerificationCase(
            slug="minimal-risk-minors",
            description="Minimal-risk study with minors",
            record=_record(
                student_researcher_names="TEST STUDENT ALPHA",
                project_title="TEST PROJECT MINORS",
                adult_sponsor="TEST SPONSOR",
                adult_sponsor_contact="555-0100 / sponsor@test.example",
                research_plan_submitted=True,
                surveys_attached=True,
                published_instruments_legally_obtained=True,
                informed_consent_attached=True,
                qualified_scientist=False,
                full_committee_review=True,
                risk_level="minimal",
                qualified_scientist_required=False,
                risk_assessment_required=False,
                minor_assent_required="yes",
                parental_permission_required="yes",
                adult_informed_consent_required="not_applicable",
            ),
        ),
        VerificationCase(
            slug="more-than-minimal-risk",
            description="More-than-minimal-risk study",
            record=_record(
                student_researcher_names="TEST STUDENT BETA",
                project_title="TEST PROJECT HIGH RISK",
                adult_sponsor="TEST SPONSOR TWO",
                adult_sponsor_contact="555-0200 / sponsor2@test.example",
                research_plan_submitted=True,
                surveys_attached=True,
                published_instruments_legally_obtained=True,
                informed_consent_attached=True,
                qualified_scientist=True,
                full_committee_review=True,
                risk_level="more_than_minimal",
                qualified_scientist_required=True,
                risk_assessment_required=True,
                minor_assent_required="yes",
                parental_permission_required="yes",
                adult_informed_consent_required="no",
            ),
        ),
        VerificationCase(
            slug="adult-only-study",
            description="Adult-only study",
            record=_record(
                student_researcher_names="TEST STUDENT GAMMA",
                project_title="TEST PROJECT ADULTS",
                adult_sponsor="TEST SPONSOR THREE",
                adult_sponsor_contact="555-0300 / sponsor3@test.example",
                research_plan_submitted=True,
                surveys_attached=False,
                published_instruments_legally_obtained=True,
                informed_consent_attached=True,
                qualified_scientist=False,
                full_committee_review=True,
                risk_level="minimal",
                qualified_scientist_required=False,
                risk_assessment_required=False,
                minor_assent_required="not_applicable",
                parental_permission_required="not_applicable",
                adult_informed_consent_required="yes",
            ),
        ),
        VerificationCase(
            slug="incomplete-draft",
            description="Incomplete draft with blank fields",
            record=_record(
                project_title="TEST INCOMPLETE DRAFT",
            ),
        ),
    ]


def _verify_coordinates() -> list[str]:
    issues: list[str] = []
    coordinates = json.loads(COORDINATES_FILE.read_text(encoding="utf-8"))
    page_width, page_height = coordinates.get("page_size", [612, 792])
    for section in ("fields", "checkboxes"):
        for name, spec in coordinates.get(section, {}).items():
            if spec["x"] < 0 or spec["y"] < 0 or spec["x"] > page_width or spec["y"] > page_height:
                issues.append(f"{section}.{name} out of page bounds")
    return issues


def main() -> None:
    if not TEMPLATE_PDF.exists():
        raise SystemExit(f"Official template missing at {TEMPLATE_PDF}")

    metadata = load_template_metadata()
    actual_hash = compute_template_sha256()
    print("template_sha256", actual_hash)
    print("expected_sha256", metadata.get("sha256"))
    print("template_version", metadata.get("template_version"))

    issues = _verify_coordinates()
    if issues:
        print("coordinate_issues", len(issues))
        for issue in issues:
            print(" -", issue)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "template_metadata_file": str(METADATA_FILE),
        "template_pdf": str(TEMPLATE_PDF),
        "template_sha256": actual_hash,
        "outputs": [],
        "manual_review_required": True,
    }

    for case in build_cases():
        document_id = uuid.uuid4()
        output_path, artifact_hash = generate_form4_pdf(document_id, case.record)
        target = OUTPUT_ROOT / f"{case.slug}.pdf"
        target.write_bytes(output_path.read_bytes())
        manifest["outputs"].append(
            {
                "slug": case.slug,
                "description": case.description,
                "path": str(target),
                "artifact_hash": artifact_hash,
            }
        )
        print("generated", target)

    manifest_path = OUTPUT_ROOT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("manifest", manifest_path)
    print("Manual visual review of generated PDFs is required.")


if __name__ == "__main__":
    main()
