# Vulnerability Report: Model Hijacking

## 1. Software/Product containing the vulnerability
Medi Guide Bot [V1.0](https://github.com/GDbateaux/305.2-applied-cybersecurity/releases/tag/1.0.0)

## 2. Vulnerability Metadata
* **Vulnerability Class:** Model Hijacking
* **CWE Identifiers:** CWE-770 (Allocation of Resources Without Limits or Throttling)
* **Estimated CVSS Score:** **5.3 (Medium)**  *Vector:* [CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L](https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L&version=3.1) 

## 3. Vulnerability Description
The Medi Guide Bot is a telegram bot with an LLM agent designed to assist patients with medical inquiries. The bot relies on a system prompt to define its behavior but this prompt is not restrictive enough to prevent users from asking the LLM wathever they want. This allows users to "hijack" the model for their personal use, consuming the bot owner's tokens.

## 4. Proof of Concept (PoC)
To demonstrate the vulnerability, a test was conducted using a standard user interaction with the bot.

Steps to Reproduce:
1. Start a conversation with the Medi Guide Bot.
2. Ask the bot for a non-medical request.

Observation : The bot completely ignores its medical context and system instructions.



https://github.com/user-attachments/assets/5aff5425-9d35-4cee-8da7-9a4b807b969d



note : the app that you can see in the video was made using streamlit to demonstrate that one can use the bot to have a free LLM-chat style app by connecting their telegram account to a python script.

## 5. Impact Analysis
While this specific example (an apple tarte tatin) is harmless, the vulnerability allows any user to consume the bot owner's tokens for any purpose, which could lead to significant financial costs if abused at scale.

## 6. How did we find the vulnerability?
This vulnerability was discovered through manual testing of the production version of the Medi Guide Bot ([V1.0](https://github.com/GDbateaux/305.2-applied-cybersecurity/releases/tag/1.0.0)). The test was performed using a standard patient account without any special privileges or tools.

## 7. When did we find the vulnerability?
This vulnerability was discovered on April 21, 2026.
