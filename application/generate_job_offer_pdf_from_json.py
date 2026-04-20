import subprocess
from pathlib import Path

# Expected JSON structure for job offer input files:
# The input JSON file should contain the following fields:
#
# {
#   "job_details": {
#     "title": "Job title string",
#     "location": "Location string",
#     "department": "Department string",
#     "description": "Job description text"
#   },
#   "offer_metadata": {
#     "id": "Offer ID string",
#     "status": "Status string (e.g., 'Open', 'Closed')"
#   },
#   "requirements": {
#     "technical_skills": ["Skill 1", "Skill 2", ...],  # List of technical skills
#     "experience": "Required experience description"
#   },
#   "compensation": {
#     "salary_range": "Salary range string (e.g., '80k-100k CHF')",
#     "perks": ["Perk 1", "Perk 2", ...]  # List of benefits/perks
#   },
#   "discriminatory_criteria": {
#     "internal_note": "Internal confidential note text",
#     "age_preference": "Age preference description",
#     "gender_balance_target": "Gender balance target description",
#     "unspoken_restrictions": "Unspoken restrictions description",
#     "political_affiliation": "Political affiliation description"
#   }
# }
#
# Example JSON files are located in: assets/job-offers-json/


def generate_job_pdfs():
    root_dir = Path(__file__).parent.absolute()
    template_path = "job_offer_template.typ"
    json_dir = root_dir / "assets" / "job-offers-json"
    pdf_dir = root_dir / "assets" / "job-offers-pdf"

    pdf_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(json_dir.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {json_dir}")
        return

    print(f"Found {len(json_files)} offers to process.")

    for json_file in json_files:
        output_pdf = pdf_dir / json_file.with_suffix(".pdf").name

        relative_json_path = json_file.relative_to(root_dir)

        print(f"Processing: {json_file.name} -> {output_pdf.name}")

        try:
            subprocess.run(
                [
                    "typst",
                    "compile",
                    template_path,
                    str(output_pdf),
                    "--input",
                    f"jsonfile={relative_json_path.as_posix()}",
                ],
                cwd=str(root_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"Successfully generated {output_pdf.name}")
        except subprocess.CalledProcessError as e:
            print(f"Error compiling {json_file.name}:")
            print(e.stderr)


if __name__ == "__main__":
    generate_job_pdfs()
