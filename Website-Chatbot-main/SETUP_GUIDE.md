# Restaurant Chatbot - Setup and Run Guide

## Overview
This is a Restaurant Chatbot application with FastAPI backend and React frontend. The chatbot can help customers with menu, hours, branches, and FAQs.

## Prerequisites
- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn

## Project Structure
```
Website-Chatbot-main/
├── app/                 # FastAPI backend
│   ├── main.py         # FastAPI server
│   ├── chatbot_logic.py # Chatbot NLP logic
│   └── test.py         # Test client
├── Frontend/           # React frontend
│   └── src/
│       └── App.jsx     # Main React component
├── data/               # JSON data files
│   ├── menu.json       # Menu items
│   ├── branches.json   # Branch locations
│   ├── hours.json      # Opening hours
│   ├── faq.json        # FAQs
│   └── about.json      # Restaurant info
└── requirements.txt    # Python dependencies
```

## Installation Steps

### 1. Backend Setup (FastAPI)

#### Step 1: Navigate to project directory
```bash
cd D:\Website-Chatbot-main
```

#### Step 2: Create virtual environment (if not exists)
```bash
python -m venv env
```

#### Step 3: Activate virtual environment

**Windows:**
```bash
env\Scripts\activate
```

**Linux/Mac:**
```bash
source env/bin/activate
```

#### Step 4: Install Python dependencies
```bash
pip install -r requirements.txt
```

#### Step 5: Start FastAPI server
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be running on: **http://127.0.0.1:8000**

You can test it at: **http://127.0.0.1:8000/docs** (Swagger UI)

### 2. Frontend Setup (React)

#### Step 1: Navigate to Frontend directory
```bash
cd Frontend
```

#### Step 2: Install dependencies
```bash
npm install
```

#### Step 3: Start development server
```bash
npm run dev
```

The frontend will be running on: **http://localhost:5173** (or another port if 5173 is busy)

## Running the Application

### Option 1: Run Both Services (Recommended)

**Terminal 1 - Backend:**
```bash
cd D:\Website-Chatbot-main
env\Scripts\activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd D:\Website-Chatbot-main\Frontend
npm run dev
```

### Option 2: Test Backend Only

You can test the backend using the test script:

```bash
cd D:\Website-Chatbot-main
env\Scripts\activate
python app\test.py
```

## Features

### Menu Categories
- 🍔 **Burgers**: Zinger Burger, Beef Royale
- 🍕 **Pizza**: Classic Margherita
- 🍝 **Pasta**: Creamy Alfredo
- 🍟 **Fries**: Signature Fries
- 🍛 **Biryani**: Chicken Biryani, Beef Biryani, Vegetable Biryani
- 🥪 **Sandwich**: Club Sandwich, Grilled Chicken Sandwich, BBQ Beef Sandwich
- 🥤 **Drinks**: Soft Drink, Iced Tea

### Chatbot Capabilities
- ✅ Show full menu with all categories and items
- ✅ Answer questions about specific menu items
- ✅ Provide opening hours for all branches
- ✅ Show branch locations and contact info
- ✅ Answer FAQs
- ✅ Understand natural language with NLP
- ✅ Handle misspellings and variations

## Example Queries

### Menu Queries:
- "Show me the menu"
- "What's in the menu"
- "What do you have"
- "Tell me about Zinger Burger"
- "What is Chicken Biryani"

### Hours Queries:
- "What are your hours"
- "When are you open"
- "Opening time"

### Branch Queries:
- "Where are your branches"
- "What is your address"
- "Contact information"

### FAQ Queries:
- "Do you offer delivery"
- "What services do you provide"

## Troubleshooting

### Backend not starting?
1. Check if port 8000 is available
2. Make sure virtual environment is activated
3. Verify all dependencies are installed: `pip install -r requirements.txt`

### Frontend not connecting to backend?
1. Make sure backend is running on port 8000
2. Check vite.config.js has proxy configuration
3. Verify CORS settings in app/main.py

### Menu not showing?
1. Check if data/menu.json exists and is valid JSON
2. Verify all data files are in the data/ directory
3. Check backend logs for errors

## API Endpoints

### POST /chat
Send a message to the chatbot.

**Request:**
```json
{
  "message": "Show me the menu"
}
```

**Response:**
```json
{
  "response": "🍽️ Our Menu:\n\n..."
}
```

## Development

### Adding New Menu Items
Edit `data/menu.json` and add items to the appropriate category.

### Adding New FAQs
Edit `data/faq.json` and add new FAQ objects.

### Modifying Chatbot Logic
Edit `app/chatbot_logic.py` to change NLP behavior or add new intents.

## Notes

- The chatbot uses fuzzy matching for better understanding of user queries
- All menu items are displayed when asking for the menu
- The frontend properly formats multi-line responses
- CORS is enabled for localhost development

## Support

For issues or questions, check:
1. Backend logs in the terminal
2. Browser console for frontend errors
3. Network tab for API calls

