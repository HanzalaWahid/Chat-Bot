from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from .chatbot_logic import load_data, get_bot_response


app = FastAPI(title="Restaurant Chatbot")

# Add CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],  # Vite default port
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
