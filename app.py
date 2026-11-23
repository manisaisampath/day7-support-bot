"""Customer Support Bot (Day 7 Challenge: risk review).

A small Flask app. A customer sends a message, the LLM decides on a reply
and an action, and the app carries out the action.
"""
import json
import logging

from flask import Flask, jsonify, request

from llm import call_llm

app = Flask(__name__)

API_KEY = "sk-demo-4f9a2c71-FAKE-KEY-for-training-only"

logging.basicConfig(filename="logs/app.log", level=logging.INFO)

ORDERS = {
    "10231": {
        "status": "Shipped",
        "amount": 1299,
        "customer_email": "ravi.kumar@example.com"
    },
    "10232": {
        "status": "Delivered",
        "amount": 499,
        "customer_email": "priya.s@example.com"
    },
    "10233": {
        "status": "Processing",
        "amount": 2499,
        "customer_email": "ravi.kumar@example.com"
    },
}
CUSTOMERS = {
    "ravi.kumar@example.com": {"name": "Ravi Kumar", "phone": "+91 98480 12345", "active": True},
    "priya.s@example.com": {"name": "Priya Sharma", "phone": "+91 99890 67890", "active": True},
}
REFUNDS = []


# ---------- Tools the LLM can use ----------

def get_order_status(order_id):
    order = ORDERS.get(order_id)
    return order["status"] if order else "Order not found"


def issue_refund(order_id, amount, customer_email):
    order = ORDERS.get(order_id)

    if not order:
        raise ValueError("Order not found")

    if customer_email not in CUSTOMERS:
        raise PermissionError("Customer not found")

    if order["customer_email"] != customer_email:
        raise PermissionError("Unauthorized refund request")

    if type(amount) is not int or amount <= 0:
        raise ValueError("Invalid refund amount")

    if amount > order["amount"]:
        raise ValueError("Refund amount exceeds order amount")

    REFUNDS.append({
        "order_id": order_id,
        "amount": amount
    })

    return f"Refunded Rs {amount} for order {order_id}"


def delete_customer_account(customer_email):
    CUSTOMERS.pop(customer_email, None)
    return f"Deleted account {customer_email}"


TOOLS = {
    "get_order_status": get_order_status,
    "issue_refund": issue_refund,
    "delete_customer_account": delete_customer_account,
}


# ---------- Chat endpoint ----------

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    email = data.get("customer_email", "")
    message = data.get("message", "")
    customer = CUSTOMERS.get(email, {})

    prompt = (
        "You are a helpful support agent. Reply in JSON with reply, action and args.\n"
        f"Customer name: {customer.get('name')}\n"
        f"Customer email: {email}\n"
        f"Customer phone: {customer.get('phone')}\n"
        f"Customer message: {message}"
    )
    logging.info("PROMPT: %s", prompt)

    text, usage = call_llm(prompt, API_KEY)
    result = json.loads(text)

    action = result.get("action")
    action_result = None

    if action:
        args = result.get("args", {})

        if args.get("customer_email") == "from_request":
            args["customer_email"] = email

        if action == "delete_customer_account":
            if email not in CUSTOMERS:
                return jsonify({
                    "reply": "Customer account not found.",
                    "action_result": None
                }), 404

            if data.get("confirm_account_deletion") is not True:
                return jsonify({
                    "reply": "Please explicitly confirm your account deletion.",
                    "action_result": None
                }), 200

        if action == "issue_refund":
            args["customer_email"] = email

        try:
            action_result = TOOLS[action](**args)
        except PermissionError as error: 
            return jsonify({
        "reply": str(error),
        "action_result": None
    }), 403
        except ValueError as error:
            return jsonify({
        "reply": str(error),
        "action_result": None
    }), 400

    logging.info("REPLY to %s: %s", email, result["reply"])
    return jsonify({"reply": result["reply"], "action_result": action_result})


if __name__ == "__main__":
    app.run(debug=True)
