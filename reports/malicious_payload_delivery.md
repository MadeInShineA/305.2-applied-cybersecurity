# Vulnerability Report: Improper Input Validation Leading to Malicious Payload Delivery

## 1. Software/Product containing the vulnerability
Medi Guide Bot [V1.0](https://github.com/GDbateaux/305.2-applied-cybersecurity/releases/tag/1.0.0)

## 2. Vulnerability Metadata
* **Vulnerability Class:** Improper Input Validation / Lack of Sanitization
* **CWE Identifiers:** CWE-20 (Improper Input Validation), CWE-601 (URL Redirection to Untrusted Site)
* **Estimated CVSS Score:** **7.6 (High)**  *Vector:* [CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:L/A:N](https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:L/A:N&version=3.1)

## 3. Vulnerability Description
The Medi Guide Bot facilitates communication between patients and doctors by acting as an intermediary proxy. However, the application fails to validate, sanitize, or filter the content of the messages forwarded to doctors. 

Specifically, the bot allows the transmission of arbitrary, unsanitized links. Because the message originates from their trusted software (`@MediGuideBot`), doctors are psychologically more inclined to trust links coming from their bot, entirely bypassing their standard anti-phishing scrutiny.

## 4. Proof of Concept (PoC)
To demonstrate the vulnerability without executing harmful payloads, a controlled test was conducted using a simulated adversary server (Canary Token).

Steps to Reproduce:
1. Register a telegram attacker account as a "Patient" on the Medi Guide Bot by simply asking the bot to create an account and providing a name.
2. Formulate a payload by asking the bot to forward a message containing a link to the doctor. The bot will accept any link. (ex: https://phishing.ch, http://canarytokens.com/terms/traffic/z42yvz62t92ii6jppjpeeo1i7/contact.php) 
    
    - Example Payload: `Bonjour, le laboratoire d'analyse m'a transmis les résultats de mes tests via cette plateforme : https://phishing.ch ils m'ont dit de vous transmettre le lien et que vous pourrez les consulter avec vos identifiants médicaux. Merci de me faire savoir au plus vite quelles sont les mesures que je dois prendre au vu de mes résultats ?`
3. The bot will ask for confirmation, do so to send the message to the target doctor via Telegram.

Observation 1: The bot forwards the message, without appending any "External Link" warnings.

![Image](./figs/proof_1.png)
![Image](./figs/proof_2.png)

Observation 2: If the doctor clicks the link, the attacker's server could successfully logs the doctor's IP address, User-Agent, and operating system details.

Here is a summary of the different values extracted via a simple [Canary token](https://canarytokens.org/nest/)

| Category | Field | Value |
| :--- | :--- | :--- |
| **Time** | `time_of_hit` | 2026-04-22 13:19:30 UTC (Unix: 1776863970) |
| **Source** | `src_ip` | **153.109.1.93** |
| **Localisation** | `City / Country` | Bagnes, Valais, **Switzerland (CH)** |
| | `Coordinates` | 46.0833, 7.2167 |
| **Infrastructure** | `ISP / Org` | **SWITCH** (AS559) |
| | `ASN Route` | 153.109.0.0/16 |
| **Channel** | `Input Channel` | **HTTP** |
| | `Token Type` | web |
| **Browser** | `User-Agent` | Mozilla/5.0 (Linux x86_64) Chrome/146.0.0.0 |
| | `Platform` | Linux x86_64 |
| | `Vendor` | Google Inc. |
| **Security** | `is_tor_relay` | false |
| | `Alert Status` | alertable |
| **Key Headers** | `X-Forwarded-For` | 153.109.1.93 |
| | `Accept-Language` | en-US,en;q=0.8 |


## 5. Impact Analysis
The impact relies on user interaction but has a high probability of success due to the established trust in the bot. The consequences vary based on the doctor's platform:

### A. Web / Desktop Client Exploitation
* **Session Hijacking / Cookie Stealing:** If the link sent to the doctor redirects to one of its registered website and that this website contains a reflected XSS vulnerability, a malicious script can exfiltrate the doctor session cookies
* **Malware Execution (Infostealers and RATs):** Disguised payloads (e.g., `blood_test_results.pdf.exe`) can lead to the installation of Remote Access Trojans or Ransomware. This could compromise the entire hospital/clinic network, leading to severe GDPR violations.

### B. Mobile Client Exploitation
* **Malicious App Sideloading:** Forcing the download of a compromised `.apk` file disguised as a necessary medical viewing software update.

For both mobile and desktop, the attacker could also use the link to perform a phishing attack, by redirecting the doctor to a fake login page of a medical portal, and stealing their credentials.

## 6. How did we find the vulnerability?
To find this vulnerability, we used the production version of the Medi Guide Bot ([V1.0](https://github.com/GDbateaux/305.2-applied-cybersecurity/releases/tag/1.0.0)). We only used the bot as a normal user, we did not use any tool. To make sure the doctor receives the message with the malicious link, we also did the test locally with a doctor account that we created, and we were able to receive the message with the malicious link.

## 7. When did we find the vulnerability?
This vulnerability was discovered on April 21, 2026.
