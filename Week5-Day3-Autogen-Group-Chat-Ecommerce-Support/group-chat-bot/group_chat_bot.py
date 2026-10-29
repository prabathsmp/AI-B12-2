import os
import autogen
from typing import Annotated
from dotenv import load_dotenv

load_dotenv(override=True)

openai_api_key = os.getenv("OPENAI_API_KEY")

config_list = [
    {
        "model": "gpt-4o-mini",
        "api_key": openai_api_key,
    }
]

llm_config = {
    "config_list": config_list,
    "temperature": 0.1,
}

# ---------------------------------------------------------
# LOCAL DATABASES
# ---------------------------------------------------------

ORDERS_DB = {
    "88492": {"status": "In Transit", "carrier": "FedEx", "tracking_no": "FDX-99812", "eta": "2 days"},
    "1234": {"status": "Processing", "carrier": "DHL", "tracking_no": "DHL-44321", "eta": "5 days"},
    "4567894": {"status": "Delivered", "carrier": "UPS", "tracking_no": "UPS-77211", "eta": "Delivered"},
}

TRANSACTIONS_DB = {
    "1234": {"amount": 89.99, "status": "Failed Checkout", "duplicate_detected": True, "refund_status": "Auto-Reversed"},
    "4567894": {"amount": 150.00, "status": "Duplicate Charge Found", "duplicate_detected": True, "refund_status": "Refund Initiated (3-5 days)"},
    "5567": {"amount": 299.00, "status": "Settled", "duplicate_detected": False, "refund_status": "Not Requested"},
}

INVENTORY_DB = {
    "monitor": {"name": "27-inch 4K Ultra Monitor", "stock": 14, "specs": "90W USB-C PD, IPS panel, 144Hz"},
    "keyboard": {"name": "Wireless Mechanical Keyboard", "stock": 0, "specs": "Hot-swappable, Bluetooth 5.2"},
}

# ---------------------------------------------------------
# TOOL FUNCTIONS
# ---------------------------------------------------------

def lookup_order_status(order_id: Annotated[str, "The order reference ID"]) -> str:
    """Fetch live order shipping status."""
    order = ORDERS_DB.get(order_id.strip())
    if not order:
        return f"Order '{order_id}' was not found in our system."
    return f"Order {order_id}: Status: {order['status']}, Carrier: {order['carrier']}, Tracking: {order['tracking_no']}, ETA: {order['eta']}."

def verify_transaction(order_id: Annotated[str, "The order reference ID"]) -> str:
    """Check payment gateway logs for duplicate charges and refunds."""
    tx = TRANSACTIONS_DB.get(order_id.strip())
    if not tx:
        return f"No transaction record found for order '{order_id}'. Please confirm the ID."
    return f"Transaction {order_id}: Status: {tx['status']}, Duplicate Found: {tx['duplicate_detected']}, Refund Status: {tx['refund_status']}."

def query_product_catalog(product_name: Annotated[str, "Product keyword"]) -> str:
    """Check stock and specs in warehouse inventory."""
    key = product_name.lower().strip()
    match = next((val for k, val in INVENTORY_DB.items() if k in key), None)
    if not match:
        return f"Product '{product_name}' not listed in local inventory."
    return f"Product: {match['name']} | In Stock: {match['stock']} | Specs: {match['specs']}."

# ---------------------------------------------------------
# AGENTS
# ---------------------------------------------------------

order_billing_agent = autogen.AssistantAgent(
    name="Order_Billing_Specialist",
    llm_config=llm_config,
    description="Handles order tracking, delivery timelines, carrier issues, and order lookup.",
    system_message="""You are the Order & Billing Specialist.
    If you need an order ID to proceed, ask the user directly (do NOT include TERMINATE).
    If an order ID is provided, use the lookup_order_status tool.
    When you have provided the final resolution, end your reply with the word 'TERMINATE'.""",
)

payment_agent = autogen.AssistantAgent(
    name="Payment_Specialist",
    llm_config=llm_config,
    description="Handles payment failures, double charges, card issues, and refund requests.",
    system_message="""You are the Payment Specialist.
    If you need an order ID to verify transactions, ask the user directly (do NOT include TERMINATE).
    When an order ID is provided, execute verify_transaction.
    When you have provided the final resolution, end your reply with the word 'TERMINATE'.""",
)

product_catalog_agent = autogen.AssistantAgent(
    name="Product_Catalog_Specialist",
    llm_config=llm_config,
    description="Handles product specs, technical compatibility, and inventory stock checks.",
    system_message="""You are the Product Catalog Specialist.
    Use query_product_catalog to look up specs and availability.
    When you have provided the final resolution, end your reply with the word 'TERMINATE'.""",
)

warranty_returns_agent = autogen.AssistantAgent(
    name="Warranty_Returns_Specialist",
    llm_config=llm_config,
    description="Handles warranty claims, defective products, returns, and replacements.",
    system_message="""You are the Warranty & Returns Specialist.
    Provide step-by-step return authorization instructions.
    When you have provided the final resolution, end your reply with the word 'TERMINATE'.""",
)

user_proxy = autogen.UserProxyAgent(
    name="Customer_Proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
    code_execution_config=False,
    is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", "").upper(),
)

# Register tools directly to the specialist agents
autogen.register_function(
    lookup_order_status,
    caller=order_billing_agent,
    executor=order_billing_agent,
    name="lookup_order_status",
    description="Check order fulfillment and tracking details.",
)

autogen.register_function(
    verify_transaction,
    caller=payment_agent,
    executor=payment_agent,
    name="verify_transaction",
    description="Check duplicate charges and refund status for an order ID.",
)

autogen.register_function(
    query_product_catalog,
    caller=product_catalog_agent,
    executor=product_catalog_agent,
    name="query_product_catalog",
    description="Check stock and hardware specs.",
)

specialists = [
    order_billing_agent,
    payment_agent,
    product_catalog_agent,
    warranty_returns_agent,
]

# ---------------------------------------------------------
# SELECTOR GROUPCHAT (Proxy excluded from next-speaker choices)
# ---------------------------------------------------------

groupchat = autogen.GroupChat(
    agents=[user_proxy] + specialists,
    messages=[],
    max_round=6,  # Allows a multi-turn back-and-forth query -> clarification -> answer
    speaker_selection_method="auto",
    select_speaker_message_template="""Read the conversation history and the latest message:
    {roles}
    CRITICAL RULE: DO NOT select Customer_Proxy. You MUST pick one of the specialist agents from: [{agentlist}]."""
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config
)

def run_support_chat(user_query: str):
    """
    Executes the selector turn while preserving prior groupchat messages
    for multi-turn context (e.g., providing an order ID when asked).
    """
    initial_msg_count = len(groupchat.messages)
    
    user_proxy.initiate_chat(
        manager,
        message=user_query,
        clear_history=False,  # KEEP HISTORY for multi-turn conversations
    )
    
    # Grab only the messages produced during this turn
    new_messages = groupchat.messages[initial_msg_count:]
    
    events = []
    for msg in new_messages:
        sender = msg.get("name", "Unknown")
        content = msg.get("content", "")
        if sender != "Customer_Proxy" and content and not msg.get("tool_calls"):
            cleaned = content.replace("TERMINATE", "").strip()
            if cleaned:
                events.append({"agent": sender, "content": cleaned})
                
    # Return only the final meaningful response from this turn
    if events:
        return [events[-1]]
    return []

def reset_chat_session():
    """Resets memory when clearing conversation in Streamlit."""
    groupchat.messages.clear()
    user_proxy.reset()
    for agent in specialists:
        agent.reset()