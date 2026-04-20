# Applied Cybersecurity - Email Job Application Agent

An automated agent that monitors an inbox for job applications, extracts CV data, verifies authenticity, matches candidates against job offers, and generates professional response emails.

## Features

- **Email Monitoring** - Polls IMAP inbox for new emails at configurable intervals
- **CV Detection** - Classifies emails as job applications by validating PDF attachment structure
- **CV Extraction** - Converts CV PDFs to structured JSON using document parsing and LLM
- **Veracity Checking** - Verifies CV claims via web search and assigns authenticity score (0-100)
- **Smart Storage** - Routes CVs to verified/unverified directories based on veracity score
- **Application Matching** - Compares verified CVs against job offers in kDrive and sets a matching score (0-100)
- **Response Generation** - Generates and sends professional email responses to applicants with match feedback
- **Job Offer PDF Generation** - Creates professional job offer PDFs from JSON data using Typst templates

## Architecture

```
main.py
generate_job_offer_pdf_from_json.py
add_hr_user.py
hr_chatbot.py
src/
├── orchestrator.py             # Main pipeline coordinator
├── mail_client.py              # IMAP/SMTP email client
├── email_classifier.py         # Job application detection
├── cv_extractor.py             # PDF to JSON extraction
├── cv_veracity_checker.py      # CV authenticity verification
├── application_matcher.py      # CV to job offer matching
├── email_answer_generator.py   # Professional response email generation
├── k_drive_tools.py            # Infomaniak kDrive API client
├── database.py                 # MySQL data persistence
└── config.py                   # Environment configuration

generate_job_offer_pdf_from_json.py  # Script to generate job offer PDFs from JSON
job_offer_template.typ                 # Typst template for job offer PDFs
```

## Setup

Please make sure you have [Uv](https://docs.astral.sh/uv/) and [Docker](https://www.docker.com/) (for local development) and [Typst](https://typst.app/) (for job offer generation) installed

Alternatively, use the provided nix flake for Uv, Python, Ruff, Typst and Tinymist :

```bash
nix develop
```

> Note: Docker must still be installed separately as it is not included in the nix flake.

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

Edit `.env` with the required environment variables

   | Variable | Description |
   |----------|-------------|
   | `OPENROUTER_API_KEY` | OpenRouter API key for LLM access |
   | `OPENROUTER_MODEL` | Model identifier (default: nvidia/nemotron-3-nano-30b-a3b) |
   | `INFOMANIAK_API_KEY` | Infomaniak API token |
   | `KDRIVE_ID` | Infomaniak kDrive ID |
   | `KDRIVE_VERIFIED_CV_DIRECTORY_ID` | Directory for verified CVs |
   | `KDRIVE_NOT_VERIFIED_CV_DIRECTORY_ID` | Directory for unverified CVs |
   | `KDRIVE_JOB_OFFERS_DIRECTORY_ID` | Directory containing job offers |
   | `DB_HOST` | MySQL host |
   | `DB_USER` | MySQL username |
   | `DB_PASSWORD` | MySQL password |
   | `DB_NAME` | MySQL database name |
   | `MAIL_SMTP_HOST` | SMTP server hostname |
   | `MAIL_SMTP_PORT` | SMTP port (e.g., 465 or 587) |
   | `MAIL_IMAP_HOST` | IMAP server hostname |
   | `MAIL_IMAP_PORT` | IMAP port (default: 993) |
   | `MAIL_EMAIL` | Email address to monitor |
   | `MAIL_PASSWORD` | Email password or app password |
   | `POLL_INTERVAL_SECONDS` | Email check interval (default: 300) |

3. **Start the MySQL and PhpMyAdmin services (for local development only)**
   ```bash
   docker compose up -d
   ```

4. **Run the application:**
   ```bash
   uv run main.py
   ```

## Pipeline Flow

1. Agent polls inbox for recent emails
2. Emails with PDF attachments are checked for CV structure
3. Valid CVs are extracted to JSON format
4. CVs are verified via web search (score 0-100)
5. CVs scoring >50 are marked as verified
6. Verified CVs are matched against job offers in kDrive
7. Professional response emails are generated and sent
8. CVs and match results are stored in the database

## Job Offer PDF Generation

Generate job offer PDFs from JSON files using Typst:

1. Place JSON files in `assets/job-offers-json/`
2. Run the generation script:
   ```bash
   uv run generate_job_offer_pdf_from_json.py
   ```
3. PDFs will be generated in `assets/job-offers-pdf/`

See `generate_job_offer_pdf_from_json.py` for the expected JSON schema.

## Dependencies

- **LLM**: OpenRouter (nvidia/nemotron-3-nano-30b-a3b)
- **Document Processing**: Docling
- **Web Search**: DuckDuckGo
- **Database**: MySQL
- **Email**: IMAP4 SSL / SMTP
- **Cloud Storage**: Infomaniak kDrive API
- **PDF Generation**: Typst
