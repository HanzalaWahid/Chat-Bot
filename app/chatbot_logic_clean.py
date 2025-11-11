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
_CANDIDATES = [_BASE / "data", _BASE / "Data"]
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
fallback = "Sorry, I didn't understand that. I can help with menu, timings, branches, or FAQs. 😊"

def normalize_text(text):
    """Normalize text for better NLP matching"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = ' '.join(text.split())
    return text

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
            if "variants" in item and isinstance(item["variants"], list):
                for v in item["variants"]:
                    if isinstance(v, dict) and "size" in v:
                        all_items.append(f"{v['size']} {item['name']}")
            if "flavours" in item and isinstance(item["flavours"], list):
                for f in item["flavours"]:
                    if isinstance(f, dict) and "name" in f:
                        all_items.append(f"{f['name']} {item['name']}")
                    elif isinstance(f, str):
                        all_items.append(f"{f} {item['name']}")
    
    if not all_items:
        return None
    
    try:
        match, score = process.extractOne(user_msg, all_items)
        if score >= 60:
            return match
    except Exception:
        pass
    return None

# Detect intent
def detect_intent(user_msg):
    msg = user_msg.lower().strip()
    
    if any(w in msg for w in ["hi", "hello", "hey", "salam", "greet"]):
        return "greeting"
    elif any(w in msg for w in ["bye", "goodbye", "see you", "farewell"]):
        return "farewell"
    elif any(w in msg for w in ["open", "hour", "timing", "time", "close", "when"]):
        return "hours_query"
    elif any(w in msg for w in ["branch", "location", "address", "where", "contact", "phone"]):
        return "branch_query"
    elif any(w in msg for w in ["about", "info", "mission", "description"]):
        return "about"
    elif any(w in msg for w in ["delivery", "veg", "vegetarian", "halal", "service", "faq"]):
        return "faq_query"
    elif any(w in msg for w in ["menu", "dish", "food", "item", "burger", "pizza", "price", "order", "what", "show"]):
        return "menu_query"
    else:
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
        wants_full = any(word in user_lower for word in ["full menu", "all menu", "complete menu", "entire menu", "show all", "all dishes", "all items"])
        
        if wants_full:
            # Display FULL MENU with all categories and items
            response = "🍽️ **OUR FULL MENU**\n\n"
            
            for category, items in menu_data.items():
                if not isinstance(items, list) or len(items) == 0:
                    continue
                
                category_name = category.upper().replace('_', ' ')
                response += f"📋 **{category_name}** ({len(items)} items)\n"
                response += "─" * 45 + "\n"
                
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
                                response += f"🌶️ **Flavours:** {', '.join(flavour_list)}\n\n"
                        
                        if "addons" in item and isinstance(item["addons"], list) and item["addons"]:
                            response += "➕ **Addons:**\n"
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
        
        response += "\n💬 Say **'full menu'** to see everything!\n"
        return response

    if intent == "branch_query":
        branches = data.get("branches", [])
        if not branches:
            return "Sorry, branch information is not available."
        
        response = "📍 **OUR BRANCHES:**\n\n"
        for b in branches:
            if not isinstance(b, dict):
                continue
            name = b.get("name", "Unknown")
            city = b.get("city", "")
            address = b.get("address", "Not available")
            phone = b.get("phone", "Not available")
            
            response += f"**{name}**"
            if city:
                response += f" ({city})"
            response += f"\n📍 {address}\n📞 {phone}\n\n"
        
        return response.strip()

    if intent == "hours_query":
        hours_list = data.get("hours", [])
        
        if not hours_list:
            return "Sorry, opening hours are not available."
        
        response = "🕐 **OPENING HOURS:**\n\n"
        
        for hours_info in hours_list:
            if not isinstance(hours_info, dict):
                continue
            
            branch_name = hours_info.get("branch_name", "Branch")
            response += f"**{branch_name}**\n"
            response += "─" * 40 + "\n"
            
            regular_hours = hours_info.get("regular", {})
            if isinstance(regular_hours, dict) and regular_hours:
                days_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                for day in days_order:
                    if day in regular_hours:
                        day_name = day.capitalize()
                        hours = regular_hours[day]
                        response += f"{day_name}: {hours}\n"
            
            special_notes = hours_info.get("special_notes", "")
            if special_notes:
                response += f"\nℹ️ {special_notes}\n"
            
            response += "\n"
        
        return response.strip()

    if intent == "faq_query":
        faqs = data.get("faq", [])
        if not faqs:
            return "Sorry, FAQ information is not available."
        
        for q in faqs:
            if not isinstance(q, dict):
                continue
            question = q.get("question", "").lower()
            answer = q.get("answer", "")
            question_words = [w for w in question.split() if len(w) > 3]
            if any(word in user_lower for word in question_words):
                return answer
        
        return "Sorry, I don't have an answer for that. You can ask about delivery, vegetarian options, halal food, or our services."

    if intent == "about":
        about_data = data.get("about", {})
        if not about_data:
            return "Sorry, restaurant information is not available."
        
        response = f"**{about_data.get('name', 'Speedy Bites')}**\n\n"
        
        if about_data.get("description"):
            response += f"{about_data['description']}\n\n"
        
        if about_data.get("mission"):
            response += f"🎯 **Mission:** {about_data['mission']}\n\n"
        
        return response.strip()

    # Fallback for unknown intent
    return fallback
