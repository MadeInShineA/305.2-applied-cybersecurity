from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openrouter import ChatOpenRouter


@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"It's always sunny in {city}!"


def main():
    load_dotenv()

    # Option 1: Pass model as string (if supported)
    # agent = create_agent("gemini-2.0-flash", [get_weather], system_prompt="You are helpful")

    # Option 2: Pass model as ChatGoogleGenerativeAI instance
    llm = ChatOpenRouter(model="nvidia/nemotron-3-nano-30b-a3b", temperature=0)
    agent = create_agent(llm, [get_weather], system_prompt="You are helpful")

    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
    ):
        print(chunk)


if __name__ == "__main__":
    main()
