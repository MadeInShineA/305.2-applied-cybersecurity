# Applied Cybersecurity - Email Job Application Agent

An automated agent that monitors an inbox for job applications, extracts CV data, verifies authenticity, and matches candidates against job offers.

## Features

- **Email Monitoring** - Polls IMAP inbox for new emails at configurable intervals
- **CV Detection** - Classifies emails as job applications by validating PDF attachment structure
- **CV Extraction** - Converts CV PDFs to structured JSON using document parsing and LLM
- **Veracity Checking** - Verifies CV claims via web search and assigns authenticity score (0-100)
- **Smart Storage** - Routes CVs to verified/unverified directories based on veracity score
- **Application Matching** - Compares verified CVs against job offers in kDrive and sets a matching score (0-100)

## Architecture

```
src/
├── orchestrator.py         # Main pipeline coordinator
├── mail_client.py           # IMAP email client
├── email_classifier.py      # Job application detection
├── cv_extractor.py          # PDF to JSON extraction
├── cv_veracity_checker.py   # CV authenticity verification
├── application_matcher.py   # CV to job offer matching
├── k_drive_tools.py         # Infomaniak kDrive API client
├── database.py              # MySQL data persistence
└── config.py                # Environment configuration
```

## Setup

Please make sure you have [uv](https://docs.astral.sh/uv/) and [Docker](https://www.docker.com/) (for local development) installed

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
   | `INFOMANIAK_API_KEY` | Infomaniak API token |
   | `KDRIVE_ID` | Infomaniak kDrive ID |
   | `KDRIVE_VERIFIED_CV_DIRECTORY_ID` | Directory for verified CVs |
   | `KDRIVE_NOT_VERIFIED_DIRECTORY_ID` | Directory for unverified CVs |
   | `KDRIVE_JOB_OFFERS_DIRECTORY_ID` | Directory containing job offers |
   | `DB_HOST` | MySQL host |
   | `DB_USER` | MySQL username |
   | `DB_PASSWORD` | MySQL password |
   | `DB_NAME` | MySQL database name |
   | `MAIL_IMAP_HOST` | IMAP server hostname |
   | `MAIL_IMAP_PORT` | IMAP port (default: 993) |
   | `MAIL_EMAIL` | Email address to monitor |
   | `MAIL_PASSWORD` | Email password or app password |
   | `POLL_INTERVAL_SECONDS` | Email check interval (default: 300) |

4. **Start the MySQL and PhpMyAdmin services (for local development only)**
    ```bash
    docker compose up -d
    ```

5. **Run the application:**
   ```bash
   uv run main.py
   ```

## Pipeline Flow

1. Agent polls inbox for recent emails
2. Emails with PDF attachments are checked for CV structure
3. Valid CVs are extracted to JSON format
4. CVs scoring >50 are marked as verified
5. Verified CVs are matched against job offers in kDrive
6. CVs are uploaded to appropriate kDrive directory

## Dependencies

- **LLM**: OpenRouter (nvidia/nemotron-3-nano-30b-a3b)
- **Document Processing**: Docling
- **Web Search**: DuckDuckGo
- **Database**: MySQL
- **Email**: IMAP4 SSL
- **Cloud Storage**: Infomaniak kDrive API
