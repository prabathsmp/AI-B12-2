from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool
import os

# Load environment variables
load_dotenv()

# Validate Serper API key
serp_key = os.getenv("SERPER_API_KEY")

if not serp_key:
    raise ValueError("SERPER_API_KEY is missing from the .env file")

# Web search tool
search_tool = SerperDevTool()

llm = LLM(
    model="ollama/qwen2.5:latest",
    base_url="http://localhost:11434"
    # model="openai/gpt-4o-mini"
)

# Agent 1: Researcher
researcher = Agent(
    role="Technology News Researcher",
    goal="Find today's top 3 technology news stories using web search",
    backstory=(
        "You are an experienced technology journalist. "
        "You search reliable news websites, verify publication dates, "
        "and identify the three most important technology stories "
        "published today."
    ),
    tools=[search_tool],
    llm=llm,
    verbose=True
)

# Agent 2: Writer
writer = Agent(
    role="Technology Newsletter Writer",
    goal="Write a concise five-line newsletter from the researcher's findings",
    backstory=(
        "You are a senior technology editor who turns research "
        "into clear, engaging newsletters. You do not conduct research "
        "or access the web. You rely exclusively on the research "
        "provided by the previous task."
    ),
    tools=[],  # Writer cannot search the web
    llm=llm,
    verbose=True
)

# Task 1: Research
find = Task(
    description=(
        "Find today's top 3 technology news stories. "
        "Use the web search tool to identify stories published today. "
        "For each story, provide its headline, a brief summary, "
        "publication date, and source URL. "
        "Return exactly 3 stories."
    ),
    expected_output=(
        "Three technology news stories, each with a headline, "
        "brief summary, publication date, and source URL."
    ),
    agent=researcher
)

# Task 2: Newsletter writing
write = Task(
    description=(
        "Using ONLY the research provided by the previous task, "
        "write a technology newsletter consisting of exactly 5 lines. "
        "Include a short introductory headline and summarize the "
        "most important findings. Do not search the web or introduce "
        "unsupported facts."
    ),
    expected_output="A concise technology newsletter containing exactly 5 lines.",
    agent=writer,
    context=[find]
)

# Create sequential crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[find, write],
    process=Process.sequential,
    verbose=True
)

# Execute workflow
result = crew.kickoff()

print("\n===== FINAL NEWSLETTER =====\n")
print(result)