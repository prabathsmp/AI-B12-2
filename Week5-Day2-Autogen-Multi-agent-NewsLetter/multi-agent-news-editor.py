import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv(override=True)


def search_weather_news(city: str) -> str:
    """Searches current news updates and live weather reports for a specified city.

    Args:
        city (str): The name of the city to look up weather news for.

    Returns:
        str: Raw search results containing recent news headlines and summaries.
    """
    try:
        results = DDGS().news(query=f"{city} weather today", max_results=5)
        return str(results)
    except Exception as e:
        return f"Error fetching news for {city}: {e}"


async def main():
    city1 = input("Enter City 1: ").strip()
    city2 = input("Enter City 2: ").strip()

    if not city1 or not city2:
        print("Please provide valid names for both cities.")
        return

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    try:
        city1_agent = AssistantAgent(
            name="city1_reporter",
            model_client=model_client,
            tools=[search_weather_news],
            reflect_on_tool_use=True,
            system_message=(
                f"You are a weather news reporter for {city1}. Use your search_weather_news tool "
                f"to gather current weather news specifically for {city1}. "
                "Provide a brief, factual summary of your findings."
            ),
        )

        city2_agent = AssistantAgent(
            name="city2_reporter",
            model_client=model_client,
            tools=[search_weather_news],
            reflect_on_tool_use=True,
            system_message=(
                f"You are a weather news reporter for {city2}. Use your search_weather_news tool "
                f"to gather current weather news specifically for {city2}. "
                "Provide a brief, factual summary of your findings."
            ),
        )

        # Reviewer validates news and uses APPROVE to instruct the editor to proceed
        reviewer_agent = AssistantAgent(
            name="news_reviewer",
            model_client=model_client,
            system_message=(
                "You are the senior news reviewer. Review the reports from city1_reporter and city2_reporter. "
                "Ensure valid weather information is present for both cities. "
                "If both reports are solid, combine the key points and state 'APPROVE' so the editor can proceed. "
                "If data is missing or invalid, explicitly ask to improve."
            ),
        )

        # Editor writes the final piece and issues the actual exit word
        editor_agent = AssistantAgent(
            name="newsletter_editor",
            model_client=model_client,
            system_message=(
                "You are the newsletter editor. Once news_reviewer says 'APPROVE', compile the approved points "
                "into a weather newsletter of at most 5 lines in total. "
                "End your message with 'PUBLISHED'."
            ),
        )

        # Terminate ONLY when the editor publishes the final piece
        termination_condition = TextMentionTermination(
            text="PUBLISHED", sources=["newsletter_editor"]
        )

        team = RoundRobinGroupChat(
            participants=[
                city1_agent,
                city2_agent,
                reviewer_agent,
                editor_agent,
            ],
            termination_condition=termination_condition,
            max_turns=8,
        )

        task = (
            f"Collect current weather news for {city1} and {city2}, review the reports, "
            f"and compile them into a weather newsletter of at most 5 lines."
        )

        await Console(team.run_stream(task=task))

    finally:
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())