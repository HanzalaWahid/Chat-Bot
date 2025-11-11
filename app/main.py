from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from .chatbot_logic import load_data, get_bot_response


app = FastAPI(title="Restaurant Chatbot")

# Add CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Load data during application startup instead of at import time.

    This avoids doing file I/O or expensive initialization when the module is
    imported (which can slow down things like test runners or tooling).
    """
    try:
        app.state.data = load_data()
    except Exception as e:
        logging.exception("Failed to load data during startup: %s", e)
        # Re-raise so the process exits and the user sees the error
        raise


class UserMessage(BaseModel):
    message: str


@app.post("/chat")
def chat(user_message: UserMessage):
    data = getattr(app.state, "data", None)
    if data is None:
        return {"response": "Service starting up, please try again in a moment."}

    response = get_bot_response(user_message.message, data)
    return {"response": response}


class QueryRequest(BaseModel):
    message: str


@app.post("/api/query")
def api_query(req: QueryRequest):
    """Frontend API endpoint that returns both answer and action buttons"""
    data = getattr(app.state, "data", None)
    if data is None:
        return {"answer": "Service starting up, please try again in a moment.", "actions": []}

    answer = get_bot_response(req.message, data)
    
    # Return relevant actions/quick-buttons based on the user's message
    actions = []
    msg_lower = req.message.lower()
    
    # If greeting, show main action buttons
    if any(word in msg_lower for word in ["hi", "hello", "hey", "greet", "start"]):
        actions = ["View Menu", "Our Branches", "Opening Hours"]
    # If they asked about menu
    elif any(word in msg_lower for word in ["menu", "dish", "food", "order", "burger", "pizza"]):
        actions = ["Full Menu", "Our Branches", "Order Online"]
    # If they asked about branches
    elif any(word in msg_lower for word in ["branch", "location", "address", "where"]):
        actions = ["View Menu", "Opening Hours", "Contact"]
    # If they asked about hours
    elif any(word in msg_lower for word in ["open", "hour", "timing", "close", "time"]):
        actions = ["View Menu", "Our Branches"]
    
    # Return in the shape the frontend expects
    return {"answer": answer, "actions": actions}