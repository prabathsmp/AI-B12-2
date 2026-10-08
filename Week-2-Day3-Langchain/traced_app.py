from langchain_openai import ChatOpenAI

llm  = ChatOpenAI(model="gpt-4o-mini")
prompts = [
    "Explain Chain component of langchain in a phrase not exceeding 10 words.",
    "Explain RAG in a phrase not exceeding 10 words.",
    "Winner between Google OKF and BM25 in a phrase not exceeding 10 words.",
]

for prompt in prompts:
    print(f"Prompt: {prompt}")
    answer = llm.invoke(prompt)
    print(f"Answer: {answer}\n")