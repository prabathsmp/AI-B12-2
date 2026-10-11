from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7
)

# Define prompt
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are Chef GPT, a helpful assistant that provides "
        "breakfast recipes using the ingredients provided."
    ),
    (
        "human",
        "I have {ingredients}. Give me {count} breakfast ideas."
    )
])

# Build chain
chain = prompt | llm | StrOutputParser() # output parser to get plain text response


# Conversational loop
while True:

    ingredients = input(
        "\nEnter your ingredients (or type 'exit' to quit): "
    ).strip()

    if ingredients.lower() in ["exit", "quit"]:
        print("Chef GPT: Goodbye! Happy cooking!")
        break

    if not ingredients:
        print("Please enter some ingredients.")
        continue

    count = input("How many breakfast ideas do you want? ").strip()

    if count.lower() in ["exit", "quit"]:
        print("Chef GPT: Goodbye! Happy cooking!")
        break

    if not count.isdigit() or int(count) < 1:
        print("Please enter a valid positive number.")
        continue

    print("\nChef GPT is thinking...\n")

    try:
        # Stream the response token by token
        for chunk in chain.stream({
            "ingredients": ingredients,
            "count": int(count)
        }):
            print(chunk, end="", flush=True)

        print("\n")

    except Exception as e:
        print(f"\nError: {e}")