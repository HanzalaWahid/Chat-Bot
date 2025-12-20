from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from chatbot_logic import load_data, get_bot_response
from fastapi import Request


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



# --- Simple in-memory session store (for demo only, not for production) ---
import uuid
from fastapi.responses import JSONResponse

user_sessions = {}

def get_session(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in user_sessions:
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {}
    session = user_sessions[session_id]
    return session_id, session

@app.post("/chat")
async def chat(user_message: UserMessage, request: Request):
    data = getattr(app.state, "data", None)
    if data is None:
        return {"response": "Service starting up, please try again in a moment."}
    session_id, session = get_session(request)
    response = get_bot_response(user_message.message, data, session)
    # Return session flags so frontend can hide buttons
    # Convert counters to booleans (frontend expects true/false)
    session_flags = {k: bool(v) for k, v in session.items() if k.startswith('shown_')}
    resp = JSONResponse({"response": response, "sessionFlags": session_flags})
    resp.set_cookie(key="session_id", value=session_id, httponly=True)
    return resp



class QueryRequest(BaseModel):
    message: str


@app.post("/api/query")
async def api_query(req: QueryRequest, request: Request):
    """Frontend API endpoint that returns both answer and action buttons, with session context."""
    data = getattr(app.state, "data", None)
    if data is None:
        return {"answer": "Service starting up, please try again in a moment.", "actions": []}
    session_id, session = get_session(request)
    answer = get_bot_response(req.message, data, session)
    actions = []
    msg_lower = req.message.lower()
    if any(word in msg_lower for word in ["hi", "hello", "hey", "greet", "start"]):
        actions = ["View Menu", "Our Branches", "Opening Hours"]
    elif any(word in msg_lower for word in ["menu", "dish", "food", "order", "burger", "pizza"]):
        actions = ["Full Menu", "Our Branches", "Order Online"]
    elif any(word in msg_lower for word in ["branch", "location", "address", "where"]):
        actions = ["View Menu", "Opening Hours", "Contact"]
    elif any(word in msg_lower for word in ["open", "hour", "timing", "close", "time"]):
        actions = ["View Menu", "Our Branches"]
    resp = JSONResponse({"answer": answer, "actions": actions})
    resp.set_cookie(key="session_id", value=session_id, httponly=True)
    return resp