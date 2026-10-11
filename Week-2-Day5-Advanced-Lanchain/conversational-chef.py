import os
import streamlit as st
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


# --------------------------------------------------
# 1. Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="AI Chef Assistant",
    page_icon="🍳",
    layout="centered"
)

st.title("🍳 Your AI Chef Assistant")

st.caption(
    "Ask for recipes, cooking tips, and meal ideas. "
    "I remember our conversation!"
)


# --------------------------------------------------
# 2. Load Environment Variables
# --------------------------------------------------

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY not found. Configure it in your .env file.")
    st.stop()


# --------------------------------------------------
# 3. Initialize LangChain Components
# --------------------------------------------------

@st.cache_resource
def init_langchain():

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are Chef GPT, a helpful cooking assistant. "
            "Suggest practical recipes, explain cooking techniques, "
            "and remember the user's preferences from the conversation."
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

    chain = prompt | llm | StrOutputParser()

    return chain


base_chain = init_langchain()


# --------------------------------------------------
# 4. Initialize Conversation Memory
# --------------------------------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = InMemoryChatMessageHistory()


def get_session_history(session_id: str):

    return st.session_state.chat_history


# Wrap the chain with conversation history.
conversational_chain = RunnableWithMessageHistory(
    base_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)


# --------------------------------------------------
# 5. Display Previous Messages
# --------------------------------------------------

for message in st.session_state.chat_history.messages:

    role = "user" if message.type == "human" else "assistant"

    with st.chat_message(role):
        st.markdown(message.content)


# --------------------------------------------------
# 6. Accept User Input and Stream Response
# --------------------------------------------------

if user_input := st.chat_input("What ingredients do you have?"):

    # Display the user's message.
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate the assistant's response.
    with st.chat_message("assistant"):

        config = {
            "configurable": {
                "session_id": "chef_session"
            }
        }

        response = st.write_stream(
            conversational_chain.stream(
                {"input": user_input},
                config=config
            )
        )