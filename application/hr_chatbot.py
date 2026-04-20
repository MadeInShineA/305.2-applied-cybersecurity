"""
Main application file for the HR Email Assistant using Chainlit.

This application integrates all modules (database, mail, CV extraction,
veracity checking, matching, and response generation) into an interactive
conversational agent.
"""

import chainlit as cl
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from docling.document_converter import DocumentConverter
from langchain_classic.memory import ConversationBufferMemory
import bcrypt
import re

# Import all custom modules
from src.config import load_config
from src.database import Database
from src.mail_client import MailClient
from src.email_classifier import EmailClassifier
from src.cv_extractor import CvExtractor
from src.cv_veracity_checker import CvVeracityChecker
from src.application_matcher import ApplicationMatcher
from src.email_answer_generator import EmailAnswerGenerator
from src.k_drive_tools import KDriveTools

# ------------------------------------------------------------------------
# 1. Initialization and Configuration
# ------------------------------------------------------------------------

# Load configuration from environment variables
config = load_config()

# Initialize external clients and database
db = Database(config)
mail_client = MailClient(config)
kdrive_tools = KDriveTools(config)

# Initialize processing modules
email_classifier = EmailClassifier(config)
document_converter = DocumentConverter()
cv_extractor = CvExtractor(config, document_converter)
cv_veracity_checker = CvVeracityChecker(config)
application_matcher = ApplicationMatcher(config, kdrive_tools)
email_answer_generator = EmailAnswerGenerator(config)

# Ensure database tables exist
db.connect()
db.ensure_tables()

# ------------------------------------------------------------------------
# 2. Define Agent Tools
# ------------------------------------------------------------------------


@tool
def check_candidate_job_matches_tool(limit_str: str = "10") -> str:
    """
    Check candidate/job matches in the database. Returns comprehensive details.
    Action Input must be a single number indicating how many matches to return (e.g., "10").

    CRITICAL DISPLAY RULE:
    When formatting these results as a Markdown table for the user, you MUST ONLY include the following columns: ID, Candidate, Email, Score, Offer, and Status.
    You MUST completely hide Strengths, Weaknesses, and Recommendations from the visual table. Keep that information internal to answer subsequent questions.
    """
    match = re.search(r"\d+", str(limit_str))
    limit = int(match.group(0)) if match else 10

    db.connect()
    matches = db.get_candidate_job_matches(limit=limit)

    if not matches:
        return "No candidate/job matches found in the database."

    results = []
    for m in matches:
        status = "Processed" if m.get("hr_email_sent") else "Pending"
        # The string returned to the LLM context remains complete
        results.append(
            f"ID: {m['id']} | Email: {m['candidate_email']} | Email Received at: {m['received_at']} | Name: {m['candidate_name']} |Score: {m['match_score']}/100 | "
            f"Offer: {m['offer_name']} | Strengths: {m['strengths']} | Weaknesses {m['weaknesses']} | Recommendations {m['recommendation']} | Status: {status}"
        )

    return "\n".join(results)


@tool
def check_match_processed_by_hr_tool(match_id: str) -> str:
    """
    Check if a candidate/job match has already been processed by HR (email sent).
    Use this tool to verify if an HR response was already sent for a specific match.
    Action Input must be the match ID (e.g., "5").
    """
    match = re.search(r"\d+", str(match_id))
    if not match:
        return "Invalid match ID. Please provide a numeric match ID."

    match_id_int = int(match.group(0))
    db.connect()

    if db.is_match_processed_by_hr(match_id_int):
        return f"Match ID {match_id_int}: Already processed by HR (email sent)."
    else:
        return f"Match ID {match_id_int}: Not yet processed by HR."


@tool
def send_email_to_candidate_tool(input_data: str) -> str:
    """
    Send an email to a candidate that HR has chosen.
    In the email you will send, shoud MUST NOT include the strengths and weaknesses regarding discriminatory criteria (e.g. age, gender, political affiliation, ...).
    Format the email using the HTML syntax to make it visually appealing.
    Action Input MUST be a single string containing 3 parts separated by a pipe character '|':
    match_id | email_subject | email_body
    Example: 2 | Interview Invitation | Dear candidate, we want to meet you on 20.04.2026...
    """
    # Split the input into exactly 3 parts: ID, Subject, Body
    parts = input_data.split("|", 2)
    if len(parts) != 3:
        return "Error: Action Input must contain match_id, subject, and body separated by '|'. STOP NOW and output this as Final Answer."

    match_id_str = parts[0].strip()
    email_subject = parts[1].strip()
    email_body = parts[2].strip()
    email_body = re.sub(
        r"[\r\n]*Observation:?\s*$", "", email_body, flags=re.IGNORECASE
    ).strip()

    # Extract numeric match_id
    match = re.search(r"\d+", str(match_id_str))
    if not match:
        return "Invalid match ID. STOP NOW and output this as Final Answer."

    match_id_int = int(match.group(0))
    db.connect()

    if db.is_match_processed_by_hr(match_id_int):
        return f"Match ID {match_id_int}: Email already sent to candidate."

    matches = db.get_candidate_job_matches(limit=100)
    target_match = next((m for m in matches if m["id"] == match_id_int), None)

    if not target_match:
        return f"Match ID {match_id_int} not found."

    candidate_email = target_match.get("candidate_email")
    offer_name = target_match.get("offer_name")

    if not candidate_email:
        return f"No candidate email found for match ID {match_id_int}."

    try:
        mail_client.connect()
        # Use the dynamic subject and body provided by the LLM
        mail_client.send_email(
            to_addresses=[candidate_email],
            subject=email_subject,
            body=email_body,
            is_html=True,
        )
        mail_client.disconnect()

        db.save_hr_response(
            match_id=match_id_int,
            candidate_email=candidate_email,
            offer_name=offer_name,
            email_subject=email_subject,
            email_body=email_body,
        )

        return (
            f"Email sent successfully to {candidate_email} with the requested content."
        )

    except Exception as e:
        return f"Error sending email: {str(e)}"


# ------------------------------------------------------------------------
# 3. LLM Setup and Agent Definition
# ------------------------------------------------------------------------

# Initialize the LLM with streaming disabled for ReAct compatibility
llm_model = ChatOpenAI(
    model=config.infomaniak_model,
    temperature=0,
    openai_api_key=config.infomaniak_ai_api_key,
    openai_api_base=config.infomaniak_base_url,
    streaming=False,
)

available_tools = [
    check_candidate_job_matches_tool,
    check_match_processed_by_hr_tool,
    send_email_to_candidate_tool,
]

# ReAct prompt overriding base alignment
react_prompt_template = """You are an HR AI Assistant. You are physically connected to the company's MySQL database, kDrive, and email server. You HAVE direct access to external data.

Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following strict format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL RULES:
1. If an Observation tells you that no records were found, you MUST stop using tools.
2. Immediately output "Thought: I now know the final answer".
3. Immediately follow with "Final Answer: [Explain that no data was found]".
4. Before sending any email, ask for confirmation with the email content.
5. You have access to the current HR user signature:
---
{hr_signature}
---
You MUST append this signature strictly inside the 'email_body' parameter when using the 'send_email_to_candidate_tool'.
You MUST NOT output this signature in your 'Final Answer'.

Previous conversation history:
{chat_history}

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

agent_prompt = PromptTemplate.from_template(react_prompt_template)


# ------------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------------


@cl.password_auth_callback
def verify_hr_credentials(username: str, password: str):
    """
    Verify HR credentials against the database and return user metadata.
    """
    db.connect()
    with db._connection.cursor() as cursor:
        cursor.execute("SELECT * FROM hr_users WHERE username = %s", (username,))
        hr_record = cursor.fetchone()

    # Validate password hash
    if hr_record and bcrypt.checkpw(
        password.encode("utf-8"), hr_record["password_hash"].encode("utf-8")
    ):
        # Store HR details in the Chainlit User metadata
        return cl.User(
            identifier=username,
            metadata={
                "full_name": hr_record["full_name"],
                "job_title": hr_record["job_title"],
                "phone": hr_record["phone"],
            },
        )

    return None


# ------------------------------------------------------------------------
# 4. Chainlit UI Events
# ------------------------------------------------------------------------


@cl.on_chat_start
async def initialize_chat_session():
    """Triggered when a user opens the Chainlit interface."""

    # Retrieve the logged-in user and build the signature block
    current_user = cl.user_session.get("user")
    hr_signature_block = (
        f"{current_user.metadata['full_name']}\n"
        f"{current_user.metadata['job_title']}\n"
        f"{current_user.metadata['phone']}"
    )
    # Store the formatted signature in the session
    cl.user_session.set("hr_signature", hr_signature_block)

    welcome_text = (
        "Welcome to the HR AI Assistant.\n"
        "I am connected to your email and database.\n\n"
        "You can ask me to:\n"
        "- Check candidate/job matches in the database\n"
        "- Check if a match has already been processed by HR\n"
        "- Send an email to a candidate that HR chose"
    )
    await cl.Message(content=welcome_text).send()

    # Create the ReAct agent
    agent_definition = create_react_agent(llm_model, available_tools, agent_prompt)

    # Initialize conversational memory
    agent_memory = ConversationBufferMemory(
        memory_key="chat_history",
        input_key="input",
        return_messages=False,  # False returns a string, which fits the ReAct text prompt
    )

    # Initialize executor with parsing error handling and memory
    agent_executor_instance = AgentExecutor(
        agent=agent_definition,
        tools=available_tools,
        verbose=True,
        handle_parsing_errors=True,
        memory=agent_memory,  # Inject memory module here
    )

    # Store agent in session
    cl.user_session.set("agent_executor", agent_executor_instance)


@cl.on_message
async def handle_user_message(message: cl.Message):
    """Process incoming user message."""

    current_agent_executor = cl.user_session.get("agent_executor")
    current_hr_signature = cl.user_session.get("hr_signature")

    # Execute agent and pass the HR signature context
    agent_response = await current_agent_executor.ainvoke(
        {"input": message.content, "hr_signature": current_hr_signature}
    )

    await cl.Message(content=agent_response["output"]).send()
