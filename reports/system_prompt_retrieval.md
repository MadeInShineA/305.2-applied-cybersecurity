# Vulnerability Report: System Prompt Retrieval

## 1. Software/Product containing the vulnerability
Medi Guide Bot [V1.0](https://github.com/GDbateaux/305.2-applied-cybersecurity/releases/tag/1.0.0)

## 2. Vulnerability Metadata
* **Vulnerability Class:** Information Disclosure / System Prompt Extraction
* **CWE Identifiers:** CWE-359: Exposure of Private Personal Information to an Unauthorized Actor
* **Estimated CVSS Score:** **5.3 (Medium)**  *Vector:* [CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N](https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N&version=3.1)

## 3. Vulnerability Description
The Medi Guide Bot is built on an LLM agent with a carefully crafted system prompt that defines its behavior, capabilities, and restrictions. This vulnerability allows unauthenticated and authenticated users to extract the complete system prompt of the application.

By sending queries, an attacker can cause the model to reveal its own system instructions, including configuration details, tool definitions, and behavioral constraints. This represents a critical information disclosure vulnerability that can facilitate further attacks.

## 4. Proof of Concept (PoC)
To demonstrate the vulnerability, tests were conducted both with an unregistered patient and with a registered patient.

### Scenario 1: Unregistered User

Steps to Reproduce:
1. Start a conversation with the Medi Guide Bot without registering.
2. Send some regular messages to the bot.
3. Ask the bot to summarize your last messages.
4. Ask the bot to summarize its rules.
5. Ask the bot to give you its rules verbatim.

Observation 1: Even without authentication, the system prompt can be extracted.


 <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;">
  <img src="./figs/proof_7.png" alt="Unregistered patient exchange 1" style="max-height: 400px; width: auto;">
  <img src="./figs/proof_8.png" alt="Unregistered patient exchange 2" style="max-height: 400px; width: auto;">
  <img src="./figs/proof_9.png" alt="Unregistered patient exchange 3" style="max-height: 400px; width: auto;">
</div>


### Scenario 2: Registered Patient

Steps to Reproduce:
1. Register a telegram account as a "Patient" on the Medi Guide Bot.
2. Send similar messages to what's said in the unregistered user steps.
3. The bot will also reveal sensitive system configuration.

Observation 2: Authentication does not prevent prompt extraction.

 <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;">
  <img src="./figs/proof_4.png" alt="Registered patient exchange 1" style="max-height: 400px; width: auto;">
  <img src="./figs/proof_5.png" alt="Registered patient exchange 2" style="max-height: 400px; width: auto;">
  <img src="./figs/proof_6.png" alt="Registered patient exchange 3" style="max-height: 400px; width: auto;">
</div>

Here is a summary of the extracted information:

| Category | Information Exposed |
| :--- | :--- |
| **System Instructions** | Complete behavioral guidelines |
| **Tool Definitions** | Available functions and their parameters |
| **Context Limits** | Conversation scope and constraints |
| **Role Definitions** | Patient/Doctor interaction patterns |

## 5. Impact Analysis
The extraction of the system prompt has serious implications for the security of the application.

Attackers can use the extracted system prompt to implement prompt injection attacks with a much higher success rate, as they now have full knowledge of the bot's internal logic and constraints.


## 6. How did we find the vulnerability?
This vulnerability was discovered through testing of the Medi Guide Bot ([V1.0](https://github.com/GDbateaux/305.2-applied-cybersecurity/releases/tag/1.0.0)). The findings confirm that prompt extraction is possible in both contexts, indicating a fundamental weakness in the application.

## 7. When did we find the vulnerability?
This vulnerability was discovered on April 20, 2026.