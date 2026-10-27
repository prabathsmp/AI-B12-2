import asyncio, os
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Load API key from .env file
load_dotenv(override=True)

async def main():
    # 1. Initialize the OpenAI model client
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    # 2. Create the HR Assistant Agent
    agent = AssistantAgent(
        name="lawyer",
        model_client=model_client,
        system_message="You are Lawyer assistant."
    )

    # 3. Prompt the agent for exactly 5 bullet points
    task = "Write a job description for a Junior Python Developer in exactly 5 bullet points, one line each."
    
    # 4. Stream and print the agent's response to the console
    await Console(agent.run_stream(task=task))
    # print(reply.messages[-1].content)
    # reply = await agent.run(task=task)
    # for m in reply.messages:
    #     print("Source:",m.source, "content:", m.content)

    # 5. Always close the client to prevent the script from hanging
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())