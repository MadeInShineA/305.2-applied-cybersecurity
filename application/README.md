# Applied Cybersecurity - Email Job Application Agent

An automated agent that monitors an inbox for job applications, extracts CV data, verifies authenticity, matches candidates against job offers, and generates professional response emails.

## Features

### Core Agent (Email Processing)
- **Email Monitoring** - Polls IMAP inbox for new emails at configurable intervals
- **CV Detection** - Classifies emails as job applications by validating PDF attachment structure
- **CV Extraction** - Converts CV PDFs to structured JSON using document parsing and LLM
- **Veracity Checking** - Verifies CV claims via web search and assigns authenticity score (0-100)
- **Smart Storage** - Routes CVs to verified/unverified directories based on veracity score
- **Application Matching** - Compares verified CVs against job offers in kDrive and sets a matching score (0-100)
- **Response Generation** - Generates and sends professional email responses to applicants with match feedback
- **Job Offer PDF Generation** - Creates professional job offer PDFs from JSON data using Typst templates

### HR Chatbot (Interactive Interface)
- **Interactive Chat Interface** - Chainlit-based conversational AI for HR staff
- **Candidate Match Review** - View all candidate/job matches with scores, strengths, and recommendations
- **HR Email Sending** - Send custom emails to candidates directly from the chat interface
- **Secure Authentication** - Password-protected access for HR users with individual credentials
- **Conversation Memory** - Maintains context across the conversation session

## Architecture

```
.
├── main.py                               # Main email agent entry point
├── generate_job_offer_pdf_from_json.py   # Script to generate job offer PDFs from JSON
├── add_hr_user.py                        # CLI script to create HR user accounts
├── hr_chatbot.py                         # Chainlit HR assistant chatbot
├── job_offer_template.typ                # Typst template for job offer PDFs
├── src/                                  # Shared modules
│   ├── orchestrator.py                   # Main pipeline coordinator
│   ├── mail_client.py                    # IMAP/SMTP email client
│   ├── email_classifier.py               # Job application detection
│   ├── cv_extractor.py                   # PDF to JSON extraction
│   ├── cv_veracity_checker.py            # CV authenticity verification
│   ├── application_matcher.py            # CV to job offer matching
│   ├── email_answer_generator.py         # Professional response email generation
│   ├── k_drive_tools.py                  # Infomaniak kDrive API client
│   ├── database.py                       # MySQL data persistence
│   └── config.py                         # Environment configuration
```

## Setup

Please make sure you have [uv](https://docs.astral.sh/uv/), [Docker](https://www.docker.com/) (for local development), and [Typst](https://typst.app/) (for job offer generation) installed.

Alternatively, use the provided nix flake for uv, Python, Ruff, Typst and Tinymist:

```bash
cd application
nix develop
```

> Note: Docker must still be installed separately as it is not included in the nix flake.

1. **Install dependencies:**
   ```bash
   cd application
   uv sync
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

Edit `.env` with the required environment variables

   | Variable | Description |
   |----------|-------------|
   | `INFOMANIAK_AI_API_KEY` | Infomaniak AI API key for HR chatbot |
   | `INFOMANIAK_BASE_URL` | Infomaniak AI base URL |
   | `INFOMANIAK_MODEL` | Infomaniak AI model identifier |
   | `INFOMANIAK_API_KEY` | Infomaniak API token for kDrive |
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
   | `CHAINLIT_AUTH_SECRET` | Secret key for Chainlit authentication (see below) |
   | `POLL_INTERVAL_SECONDS` | Email check interval (default: 300) |

3. **Generate Chainlit authentication secret:**
   ```bash
   uv run chainlit create-secret
   ```
   Copy the generated key and paste it into the `CHAINLIT_AUTH_SECRET` field in your `.env` file.

4. **Start the MySQL and PhpMyAdmin services (for local development only)**
   ```bash
   docker compose up -d
   ```

5. **Create an HR user account:**
   ```bash
   uv run add_hr_user.py
   ```
   Follow the prompts to create an HR user with username, password, full name, job title, and phone number.

## Running the Applications

### Core Email Agent
Run the main email processing agent:
```bash
uv run main.py
```

### HR Chatbot
Run the interactive HR chatbot:
```bash
uv run chainlit run hr_chatbot.py
```
Then open http://localhost:8000 in your browser and log in with your HR credentials.

## Pipeline Flow

### Core Agent
1. Agent polls inbox for recent emails
2. Emails with PDF attachments are checked for CV structure
3. Valid CVs are extracted to JSON format
4. CVs are verified via web search (score 0-100)
5. CVs scoring >50 are marked as verified
6. Verified CVs are matched against job offers in kDrive
7. Professional response emails are generated and sent
8. CVs and match results are stored in the database

### HR Chatbot
1. HR user logs in with username and password
2. User can ask to see candidate/job matches
3. User can check if a match has been processed
4. User can compose and send custom emails to candidates
5. Sent emails are recorded in the database

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

- **LLM**: OpenRouter (core agent) / Infomaniak AI (HR chatbot)
- **Document Processing**: Docling
- **Web Search**: DuckDuckGo
- **Database**: MySQL
- **Email**: IMAP4 SSL / SMTP
- **Cloud Storage**: Infomaniak kDrive API
- **PDF Generation**: Typst
- **Chat Interface**: Chainlit
- **Authentication**: bcrypt
