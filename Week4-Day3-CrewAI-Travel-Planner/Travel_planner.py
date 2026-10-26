from dotenv import load_dotenv
from crewai import Agent, LLM, Task, Crew

# Load environment variables
load_dotenv()

# Get city from user
city = input("Which city? ")

# Configure Ollama LLM
ollama_llm = LLM(
    model="ollama/qwen2.5:latest",
    base_url="http://localhost:11434"
)

# Define the travel planner agent
planner = Agent(
    role="Veteran Travel Planner",
    goal="Suggest 3 places to visit in {city}",
    backstory=(
        "You have worked with more than 1000 domestic clients "
        "across India for 20 years."
    ),
    llm=ollama_llm,
    verbose=False,
    allow_delegation=False
)

print("Planner is ready!")

# Define the task
itinerary = Task(
    description="Suggest the 3 best places to visit in {city}. "
                "The city is provided as an input. "
                "Do not ask the user for the city again.",
    expected_output=(
        "Three places of interest in the specified city, "
        "including a brief description and things to do at each place."
    ),
    agent=planner
)

print("Task is ready!")

# Create the crew
crew = Crew(
    agents=[planner],
    tasks=[itinerary],
    verbose=False
)

# IMPORTANT: Pass the city input to CrewAI
result = crew.kickoff(inputs={"city": city})

# Display the result
print("\nTravel Recommendations:")
print(result)
