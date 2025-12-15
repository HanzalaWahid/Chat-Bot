import json
import random
import re
from fuzzywuzzy import fuzz, process
from pathlib import Path

# Determine the data directory robustly. The repository stores JSON under either
# "Data" or "data" at the project root; try both so the code works on case-
# sensitive filesystems as well as Windows.
_BASE = Path(__file__).resolve().parent.parent
# Prefer the lowercase `data` directory (common convention). If it doesn't
# exist, fall back to `Data` for compatibility with older repo copies.
_CANDIDATES = [_BASE / "data", _BASE / "Data", _BASE / "app" / "data"]
DATA_DIR = None
for p in _CANDIDATES:
    if p.exists() and p.is_dir():
        DATA_DIR = p
        break
if DATA_DIR is None:
    raise FileNotFoundError(f"Could not find a data directory. Tried: {', '.join(str(p) for p in _CANDIDATES)}")

# Load all JSON files once
def load_data():
    data = {}
    # Load menu.json - structure: {"restaurant": "...", "currency": "...", "menu": {...}}
    with (DATA_DIR / "menu.json").open("r", encoding="utf-8") as f:
        menu_json = json.load(f)
        # Extract the menu object (it's nested under "menu" key)
        data["menu"] = menu_json.get("menu", menu_json)
        data["restaurant_name"] = menu_json.get("restaurant", "Restaurant")
        data["currency"] = menu_json.get("currency", "PKR")

    # Load faq.json - structure: {"faqs": [...]}
    with (DATA_DIR / "faq.json").open("r", encoding="utf-8") as f:
        faq_json = json.load(f)
        data["faq"] = faq_json.get("faqs", [])

    # Load about.json - structure: {"id": "...", "name": "...", "mission": "...", etc.}
    with (DATA_DIR / "about.json").open("r", encoding="utf-8") as f:
        data["about"] = json.load(f)

    # Load branches.json - structure: {"branches": [...]}
    with (DATA_DIR / "branches.json").open("r", encoding="utf-8") as f:
        branches_json = json.load(f)
        data["branches"] = branches_json.get("branches", [])

    # Load hours.json - structure: {"hours": [...]}
    with (DATA_DIR / "hours.json").open("r", encoding="utf-8") as f:
        hours_json = json.load(f)
        data["hours"] = hours_json.get("hours", [])

    return data

# Predefined responses
greetings = [
    "Hi! 👋 Welcome to Speedy Bites! How can I help you today?",
    "Hello! Welcome to Speedy Bites! 🍽️ What would you like?",
    "Hey there! 👋 Welcome to Speedy Bites! What can I do for you?"
]
farewells = ["Bye! Have a great day!", "See you soon!", "Thanks for visiting Speedy Bites!"]
fallback = "Sorry, I didn't understand that. I can help with menu, opening hours, branches, or FAQs. 😊"

# Synonym dictionary for better NLP understanding
SYNONYMS = {
    # Menu related
    "menu": ["menu", "card", "list", "items", "dishes", "food", "catalog", "selection"],
    "dish": ["dish", "item", "food", "meal", "course", "plate"],
    "show": ["show", "display", "see", "view", "list", "tell", "give", "provide"],
    "what": ["what", "which", "tell me", "i want to know"],
    "price": ["price", "cost", "rate", "charge", "fee", "amount", "how much"],
    
    # Hours related
    "hours": ["hours", "timing", "time", "schedule", "open", "opening", "close", "closing"],
    "when": ["when", "what time", "at what time"],
    "open": ["open", "opens", "opening", "available", "operational"],
    "close": ["close", "closes", "closing", "closed"],
    
    # Location related
    "branch": ["branch", "location", "outlet", "store", "shop", "restaurant"],
    "address": ["address", "location", "where", "place", "venue"],
    "phone": ["phone", "contact", "number", "telephone", "call"],
    
    # General
    "have": ["have", "serve", "offer", "provide", "sell", "available"],
    "can": ["can", "could", "able", "possible"],
    "do": ["do", "does", "is", "are", "was", "were"],
}

# Intent keywords with synonyms
INTENT_KEYWORDS = {
    "greeting": [
        "hi", "hello", "hey", "salam", "assalam", "good morning", "good afternoon", 
        "good evening", "greetings", "hi there", "hello there"
    ],
    "farewell": [
        "bye", "goodbye", "see you", "farewell", "later", "take care", "see ya",
        "goodbye", "ciao", "adios"
    ],
    "hours_query": [
        "open", "opening", "opens", "close", "closing", "closes", "hours", "hour",
        "timing", "timings", "time", "schedule", "when", "what time", "available",
        "operational", "working hours", "business hours", "opening hours",
        "what are your hours", "days"
    ],
    "branch_query": [
        "branch", "branches", "location", "locations", "address", "addresses",
        "phone", "contact", "where", "find", "locate", "outlet", "outlets",
        "store", "stores", "shop", "near me", "our branches",
        "where are your branches"
    ],
    "about": [
        "about", "information", "info", "tell me about", "who are you", "what is",
        "describe", "details", "background", "story", "history"
    ],
    "faq_query": [
        "delivery", "deliver", "veg", "vegetarian", "halal", "service", "services",
        "do you", "does", "can you", "can i", "is it", "are you", "do they",
        "question", "help", "support", "do you offer delivery"
    ],
    "menu_query": [
        "menu", "dish", "dishes", "food", "item", "items", "order", "burger",
        "pizza", "pasta", "drink", "fries", "price", "prices", "cost", "how much",
        "variants", "flavours", "flavors", "show", "what", "list", "see", "available",
        "have", "serve", "what's", "what is", "what are", "tell me", "show me",
        "give me", "i want", "can i get", "what do you have", "what do you serve",
        "what can i order", "what options", "selection", "view", "view menu",
        "show me the menu"
    ]
}

def normalize_text(text):
    """Normalize text for better NLP matching"""
    # Convert to lowercase
    text = text.lower().strip()
    
    # Remove special characters but keep spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Expand contractions
    contractions = {
        "what's": "what is",
        "what're": "what are",
        "who's": "who is",
        "where's": "where is",
        "when's": "when is",
        "why's": "why is",
        "how's": "how is",
        "it's": "it is",
        "that's": "that is",
        "there's": "there is",
        "here's": "here is",
        "i'm": "i am",
        "you're": "you are",
        "we're": "we are",
        "they're": "they are",
        "i've": "i have",
        "you've": "you have",
        "we've": "we have",
        "they've": "they have",
        "i'll": "i will",
        "you'll": "you will",
        "we'll": "we will",
        "they'll": "they will",
        "don't": "do not",
        "doesn't": "does not",
        "didn't": "did not",
        "can't": "cannot",
        "won't": "will not",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
    }
    
    for contraction, expansion in contractions.items():
        text = text.replace(contraction, expansion)
    
    return text

def expand_synonyms(text, synonym_dict):
    """Expand text with synonyms for better matching"""
    words = text.split()
    expanded_words = []
    
    for word in words:
        # Check if word is in any synonym group
        found_synonym = False
        for key, synonyms in synonym_dict.items():
            if word in synonyms:
                expanded_words.extend(synonyms)
                found_synonym = True
                break
        if not found_synonym:
            expanded_words.append(word)
    
    return ' '.join(expanded_words)

def calculate_intent_score(user_msg, intent_keywords):
    """Calculate similarity score between user message and intent keywords"""
    user_words = set(user_msg.split())
    scores = []
    
    for keyword in intent_keywords:
        # Direct word match
        if keyword in user_words:
            scores.append(100)
        else:
            # Fuzzy match with individual words
            best_match = 0
            for user_word in user_words:
                if len(user_word) > 2 and len(keyword) > 2:
                    similarity = fuzz.ratio(user_word, keyword)
                    best_match = max(best_match, similarity)
            scores.append(best_match)
    
    # Also check for phrase matching
    for keyword in intent_keywords:
        if len(keyword.split()) > 1:  # Multi-word keyword
            similarity = fuzz.partial_ratio(user_msg, keyword)
            scores.append(similarity)
    
    return max(scores) if scores else 0

def fuzzy_word_in_text(word, text, threshold=70):
    """Check if a word (with fuzzy matching) exists in text"""
    text_words = text.split()
    for text_word in text_words:
        if fuzz.ratio(word.lower(), text_word.lower()) >= threshold:
            return True
    return False

# Helper to search menu items
def search_menu(user_msg, menu_data):
    all_items = []
    for category, items in menu_data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or "name" not in item:
                continue
            all_items.append(item["name"])
            # Include variants
            if "variants" in item and isinstance(item["variants"], list):
                for v in item["variants"]:
                    if isinstance(v, dict) and "size" in v:
                        all_items.append(f"{v['size']} {item['name']}")
            # Include flavours
            if "flavours" in item and isinstance(item["flavours"], list):
                for f in item["flavours"]:
                    if isinstance(f, dict) and "name" in f:
                        all_items.append(f"{f['name']} {item['name']}")
                    elif isinstance(f, str):
                        all_items.append(f"{f} {item['name']}")
    
    # Handle empty menu or no matches
    if not all_items:
        return None
    
    try:
        match, score = process.extractOne(user_msg, all_items)
        if score >= 60:  # similarity threshold
            return match
    except Exception:
        # If extractOne fails, return None
        pass
    return None

# Detect intent with improved NLP and flexibility
def detect_intent(user_msg):
    # Normalize the message
    normalized_msg = normalize_text(user_msg)
    
    # Special cases for button actions
    if normalized_msg == "show me the menu":
        return "menu_query"
    if normalized_msg == "what are your hours":
        return "hours_query"
    if normalized_msg == "where are your branches":
        return "branch_query"
    if normalized_msg == "do you offer delivery":
        return "faq_query"
    
    # Force intents based on key words
    if "menu" in normalized_msg:
        return "menu_query"
    if "delivery" in normalized_msg or "deliver" in normalized_msg:
        return "faq_query"
    if "hours" in normalized_msg or "opening" in normalized_msg or "time" in normalized_msg or "days" in normalized_msg:
        return "hours_query"
    if "branch" in normalized_msg or "location" in normalized_msg or "address" in normalized_msg:
        return "branch_query"
    if "about" in normalized_msg or "mission" in normalized_msg or "info" in normalized_msg:
        return "about"
    
    # Calculate scores for each intent
    intent_scores = {}
    
    # Check each intent with improved matching
    for intent, keywords in INTENT_KEYWORDS.items():
        score = calculate_intent_score(normalized_msg, keywords)
        
        # Also check for direct keyword matches (case-insensitive)
        for keyword in keywords:
            if keyword in normalized_msg:
                score = max(score, 100)
            # Check for partial phrase matches
            if len(keyword.split()) > 1:
                if fuzz.partial_ratio(normalized_msg, keyword) > 80:
                    score = max(score, 90)
        
        intent_scores[intent] = score
    
    # Special handling for greetings (should have high priority if detected)
    if intent_scores.get("greeting", 0) > 60:
        return "greeting"
    
    # Special handling for farewells
    if intent_scores.get("farewell", 0) > 60:
        return "farewell"
    
    # Check for FAQ query
    if intent_scores.get("faq_query", 0) > 60:
        return "faq_query"
    
    # Check for about query (but not if menu is mentioned)
    if intent_scores.get("about", 0) > 60 and "menu" not in normalized_msg:
        return "about"
    
    # Check for hours query (but not if it's clearly about menu)
    if intent_scores.get("hours_query", 0) > 60:
        return "hours_query"
    
    # Check for branch query
    if intent_scores.get("branch_query", 0) > 60:
        return "branch_query"
    
    # Menu query - most common, use lower threshold
    if intent_scores.get("menu_query", 0) > 40:
        return "menu_query"
    
    # If we have any score above 40, use the highest
    max_score = max(intent_scores.values())
    if max_score > 40:
        best_intent = max(intent_scores, key=intent_scores.get)
        return best_intent
    
    # Default to menu_query for short unclear messages
    if len(normalized_msg.split()) <= 4:
        return "menu_query"
    
    return "unknown"

# Generate chatbot response
def get_bot_response(user_msg, data):
    intent = detect_intent(user_msg)
    user_lower = user_msg.lower().strip()

    if intent == "greeting":
        return random.choice(greetings)

    if intent == "farewell":
        return random.choice(farewells)

    if intent == "menu_query":
        menu_data = data.get("menu", {})
        currency = data.get("currency", "PKR")
        
        if not menu_data:
            return "Sorry, the menu is currently unavailable."
        
        # Check if user wants FULL menu
        wants_full = any(word in user_lower for word in ["full menu", "all menu", "complete menu", "entire menu", "show all", "all dishes", "all items", "view menu"])
        
        if wants_full:
            # Display FULL MENU with all categories and items
            response = "🍽️ OUR FULL MENU\n\n"
            
            for category, items in menu_data.items():
                if not isinstance(items, list) or len(items) == 0:
                    continue
                
                category_name = category.upper().replace('_', ' ')
                response += f"📋 {category_name} ({len(items)} items)\n"
                response += "─" * 30 + "\n"
                
                for idx, item in enumerate(items, 1):
                    if not isinstance(item, dict) or "name" not in item:
                        continue
                    
                    response += f"{idx}. {item['name']}"
                    
                    # Add price info
                    if "variants" in item and isinstance(item["variants"], list) and item["variants"]:
                        prices = [v.get("price", 0) for v in item["variants"] if isinstance(v, dict) and "price" in v]
                        if prices:
                            min_price = min(prices)
                            max_price = max(prices)
                            if len(prices) == 1:
                                response += f" — {min_price} {currency}"
                            else:
                                response += f" — {min_price}-{max_price} {currency}"
                    elif "base_price" in item:
                        response += f" — {item['base_price']} {currency}"
                    
                    response += "\n"
                
                response += "\n"
            
            response += "💡 Ask me about any dish for details or order now!\n"
            return response
        
        # Search for SPECIFIC dish by name
        match = search_menu(user_msg, menu_data)
        if match:
            for category, items in menu_data.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or "name" not in item:
                        continue
                    if match.lower() in item["name"].lower():
                        response = f"🍽️ **{item['name']}**\n"
                        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        
                        if item.get('description'):
                            response += f"📝 {item['description']}\n\n"
                        
                        if "variants" in item and isinstance(item["variants"], list) and item["variants"]:
                            response += "💰 **Prices:**\n"
                            for v in item["variants"]:
                                if isinstance(v, dict) and "size" in v and "price" in v:
                                    response += f"  • {v['size']}: {v['price']} {currency}\n"
                            response += "\n"
                        
                        if "flavours" in item and isinstance(item["flavours"], list) and item["flavours"]:
                            flavour_list = []
                            for f in item["flavours"]:
                                if isinstance(f, dict) and "name" in f:
                                    flavour_list.append(f['name'])
                                elif isinstance(f, str):
                                    flavour_list.append(f)
                            if flavour_list:
                                response += f"🌶️ Flavors: {', '.join(flavour_list)}\n\n"
                        
                        if "addons" in item and isinstance(item["addons"], list) and item["addons"]:
                            response += "➕ Add-ons:\n"
                            for a in item["addons"]:
                                if isinstance(a, dict) and "name" in a and "price" in a:
                                    response += f"  • {a['name']} — +{a['price']} {currency}\n"
                        
                        return response.strip()
        
        # If no specific match, show popular items
        response = "🍽️ **Popular Items:**\n\n"
        sample_count = 0
        for category, items in menu_data.items():
            if not isinstance(items, list) or len(items) == 0:
                continue
            for item in items:
                if not isinstance(item, dict) or "name" not in item:
                    continue
                response += f"• {item['name']}"
                if "variants" in item and isinstance(item["variants"], list) and item["variants"]:
                    prices = [v.get("price", 0) for v in item["variants"] if isinstance(v, dict) and "price" in v]
                    if prices:
                        response += f" — {min(prices)} {currency}+"
                elif "base_price" in item:
                    response += f" — {item['base_price']} {currency}"
                response += "\n"
                sample_count += 1
                if sample_count >= 4:
                    break
            if sample_count >= 4:
                break
        
        response += "\n💬 Say 'full menu' to see everything!\n"
        return response

    if intent == "branch_query":
        branches = data.get("branches", [])
        if not branches:
            return "Sorry, branch information is not available."
        
        response = "📍 OUR BRANCHES:\n\n"
        for b in branches:
            if not isinstance(b, dict):
                continue
            name = b.get("name", "Unknown")
            city = b.get("city", "")
            address = b.get("address", "Not available")
            phone = b.get("phone", "Not available")
            
            response += f"{name}"
            if city:
                response += f" ({city})"
            response += f"\n"
            response += f"📍 {address}\n"
            response += f"📞 {phone}\n\n"
        
        return response.strip()

    if intent == "hours_query":
        hours_list = data.get("hours", [])
        
        if not hours_list:
            return "Sorry, opening hours are not available."
        
        response = "🕐 OPENING HOURS:\n\n"
        
        for hours_info in hours_list:
            if not isinstance(hours_info, dict):
                continue
            
            branch_name = hours_info.get("branch_name", "Branch")
            response += f"**{branch_name}**\n"
            
            regular_hours = hours_info.get("regular", {})
            if isinstance(regular_hours, dict) and regular_hours:
                days_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                for day in days_order:
                    if day in regular_hours:
                        day_name = day.capitalize()
                        hours = regular_hours[day]
                        response += f"**{day_name:<12}**{hours}\n"
            
            special_notes = hours_info.get("special_notes", "")
            if special_notes:
                response += f"\nℹ️ {special_notes}\n"
            
            response += "\n"
        
        return response.strip()

    if intent == "faq_query":
        faqs = data.get("faq", [])
        if not faqs:
            return "Sorry, FAQ information is not available."
        
        # Try to find matching FAQ
        for q in faqs:
            if not isinstance(q, dict):
                continue
            question = q.get("question", "").lower()
            answer = q.get("answer", "")
            question_words = [w for w in question.split() if len(w) > 3]
            if any(word in user_lower for word in question_words):
                return answer
        
        # If no match, show common FAQs
        return "Sorry, I don't have an answer for that. You can ask about delivery, vegetarian options, halal food, or our services."

    if intent == "about":
        about_data = data.get("about", {})
        if not about_data:
            return "Sorry, restaurant information is not available."
        
        response = f"{about_data.get('name', 'Speedy Bites')}\n\n"
        
        if about_data.get("description"):
            response += f"{about_data['description']}\n\n"
        
        if about_data.get("mission"):
            response += f"🎯 Mission: {about_data['mission']}\n\n"
        
        return response.strip()
    # Fallback for unknown intent
    return fallback

