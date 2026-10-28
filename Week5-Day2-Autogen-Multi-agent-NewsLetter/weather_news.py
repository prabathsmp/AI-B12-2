import asyncio
import os
from dotenv import load_dotenv
from ddgs import DDGS
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 1. Load the OpenAI API key from the .env file
load_dotenv(override=True)


# 2. Define the search tool with type hints and a clear docstring
def search_weather_news(city: str) -> str:
    """Searches current news updates and live weather reports for a specified city.

    Args:
        city (str): The name of the city to look up weather news for.

    Returns:
        str: Raw search results containing recent news headlines and summaries.
    """
    results = DDGS().news(query=f"{city} weather today", max_results=5)
    return str(results)


async def main():
    # 3. Get user input for the city
    city = input("Which city? ").strip()
    if not city:
        print("Please enter a valid city name.")
        return

    # 4. Initialize the OpenAI model client (reads OPENAI_API_KEY from environment)
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    try:
        # 5. Create the AssistantAgent with the tool and explicit formatting instructions
        agent = AssistantAgent(
            name="weather_news",
            model_client=model_client,
            tools=[search_weather_news],
            system_message=(
                "You are a weather news assistant. Always use the search_weather_news tool "
                "to find today's weather news for the requested city. "
                "Synthesize the findings and reply in exactly 3 short lines."
            ),
            reflect_on_tool_use=True,
        )

        # 6. Stream the agent's execution to the console
        task_prompt = f"Find the current weather news for {city} and summarize it in exactly 3 short lines."
        await Console(agent.run_stream(task=task_prompt))

    finally:
        # 7. Always ensure the client is closed cleanly
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())