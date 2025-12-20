import json
import random
import re
from rapidfuzz import fuzz, process
# from fuzzywuzzy import fuzz, processF
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent

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
        "describe", "details", "background", "story", "history",
        "famous", "speciality", "special", "best", "quality", "food bite", "speedy bites"
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
    ],
    "halal_query": [
        "halal", "is it halal", "is food halal", "haram"
    ],
    "brand_query": [
        "what is speedy bites", "what is food bite", "who are you", "what are you", "brand", "company"
    ]
}

# Known categories that are currently unavailable but recognized
KNOWN_UNAVAILABLE_CATEGORIES = {
    "roll": "rolls",
    "rolls": "rolls",
    "role": "rolls",
    "wrap": "wraps",
    "soup": "soups"
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
        # rapidfuzz returns (match, score, index)
        match_result = process.extractOne(user_msg, all_items)
        if match_result:
            match = match_result[0]
            score = match_result[1]
            if score >= 60:  # similarity threshold
                return match
    except Exception:
        pass
    return None

def clean_search_query(text):
    """Remove common stop words to focus on the core search term."""
    stop_words = [
        "what", "is", "the", "price", "of", "how", "much", "does", "cost", 
        "show", "me", "tell", "about", "i", "want", "to", "order", "have", 
        "you", "got", "list", "menu", "available", "can", "get", "a", "an",
        "in", "for", "please", "help", "need", "looking", "find", "search",
        "but", "asked", "meant", "say", "said"
    ]
    words = text.lower().split()
    filtered = [w for w in words if w not in stop_words]
    return " ".join(filtered)

def search_category_or_dish(user_msg, menu_data):
    """
    Search for a category first, then a dish using improved fuzzy matching.
    """
    cleaned_msg = clean_search_query(user_msg)
    if not cleaned_msg:
        cleaned_msg = user_msg  # Fallback if everything was stripped
        
    # 1. Get best category match
    best_cat = None
    cat_score = 0
    categories = list(menu_data.keys())
    
    # Use token_set_ratio for categories to handle "show me burgers" -> "burgers"
    cat_result = process.extractOne(cleaned_msg, categories, scorer=fuzz.token_set_ratio)
    if cat_result and cat_result[1] >= 80:
        best_cat = cat_result[0]
        cat_score = cat_result[1]

    # 2. Get best dish match
    best_dish = None
    dish_score = 0
    
    all_items = []
    dish_map = {} # Map lower-case name to original name
    
    for category, items in menu_data.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "name" in item:
                    name = item["name"]
                    all_items.append(name)
                    dish_map[name.lower()] = name
                    
                    # Add variants to search
                    if "variants" in item and isinstance(item["variants"], list):
                         for v in item["variants"]:
                             if isinstance(v, dict) and "size" in v:
                                 var_name = f"{v['size']} {name}"
                                 all_items.append(var_name)
                                 dish_map[var_name.lower()] = name # Map variant to main dish name

    # Use token_set_ratio for partials like "price of zinger" -> "Zinger Burger"
    # and "WRatio" or "partial_ratio" for robustness
    dish_result = process.extractOne(cleaned_msg, all_items, scorer=fuzz.token_set_ratio)
    
    if dish_result:
         score = dish_result[1]
         # Boost score for exact substring matches
         if cleaned_msg.lower() in dish_result[0].lower():
             score = max(score, 95)
             
         if score >= 60:
            best_dish = dish_result[0]
            dish_score = score
            
            # Map back to main dish name if it was a variant
            if best_dish.lower() in dish_map:
                best_dish = dish_map[best_dish.lower()]

    # 3. Decision Logic
    
    # strong category match
    if best_cat and cat_score > 85: 
        # Unless dish is vastly better (unlikely if cat is > 85)
        if best_dish and dish_score > cat_score + 10:
             return {"type": "dish", "data": best_dish}
        return {"type": "category", "data": best_cat, "items": menu_data[best_cat]}

    # strong dish match
    if best_dish and dish_score > 80:
        return {"type": "dish", "data": best_dish}
        
    # ambiguous / weak matches
    if best_cat and best_dish:
        if cat_score >= dish_score:
             return {"type": "category", "data": best_cat, "items": menu_data[best_cat]}
        else:
             return {"type": "dish", "data": best_dish}
             
    if best_cat:
        return {"type": "category", "data": best_cat, "items": menu_data[best_cat]}
        
    if best_dish:
        return {"type": "dish", "data": best_dish}

    return None

def build_category_response(category_name, items, currency):
    """Format all items in a category with prices."""
    cat_display = category_name.upper().replace('_', ' ')
    response = f"🍽️ **{cat_display}**\n"
    response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for item in items:
        if not isinstance(item, dict) or "name" not in item:
            continue
        response += f"• **{item['name']}**"
        
        # Add price info
        if "variants" in item and isinstance(item["variants"], list) and item["variants"]:
            prices = [v.get("price", 0) for v in item["variants"] if isinstance(v, dict) and "price" in v]
            if prices:
                if len(prices) == 1:
                    response += f" — {min(prices)} {currency}"
                else:
                    response += f" — {min(prices)}-{max(prices)} {currency}"
        elif "base_price" in item:
            response += f" — {item['base_price']} {currency}"
        response += "\n"
    
    response += "\n💡 Type a specific dish name for more details!"
    return response

# Detect intent with improved NLP and flexibility
def detect_intent(user_msg):
    # Normalize the message
    normalized_msg = normalize_text(user_msg)
    
    # Special cases for button actions (MUST PRESERVE)
    if normalized_msg == "show me the menu":
        return "menu_query"
    if "price" in normalized_msg or "how much" in normalized_msg:
        return "menu_query"
    if normalized_msg == "what are your hours":
        return "hours_query"
    if normalized_msg == "where are your branches":
        return "branch_query"
    if normalized_msg == "do you offer delivery":
        return "faq_query"
    
    # 1. Explicit Menu Requests (Highest Priority)
    menu_keywords = ["show me the menu", "view menu", "see menu", "full menu", "all menu", "complete menu", "menu"]
    for kw in menu_keywords:
         if kw in normalized_msg:
             return "menu_query"
             
    # 2. Price Requests
    if "price" in normalized_msg or "how much" in normalized_msg or "cost" in normalized_msg:
        return "menu_query" # Handled within menu_query logic to extract item
        
    # 3. Goodbye/Exit (Strict)
    goodbye_keywords = ["bye", "exit", "quit", "goodbye", "see you", "farewell"]
    user_words = normalized_msg.split()
    if any(w in goodbye_keywords for w in user_words):
        return "farewell"
        
    # 4. Halal Query
    if "halal" in normalized_msg or "haram" in normalized_msg:
        return "halal_query"
        
    # 5. Brand/About Query
    if "what is speedy bites" in normalized_msg or "what is food bite" in normalized_msg or "brand" in normalized_msg or "company" in normalized_msg:
        return "brand_query"
    if "famous" in normalized_msg or "speciality" in normalized_msg: 
        return "brand_query"
    # Rule A: Broad Brand Checks
    if "speed bite" in normalized_msg or "who are we" in normalized_msg or "about you" in normalized_msg or "tell me about" in normalized_msg:
         return "brand_query"
        
    # 6. Branch/Location
    if "branch" in normalized_msg or "location" in normalized_msg or "address" in normalized_msg or "where" in normalized_msg:
        return "branch_query"

    # 7. Hours
    if "hours" in normalized_msg or "open" in normalized_msg or "time" in normalized_msg or "when" in normalized_msg:
         return "hours_query"

    # 8. Delivery/FAQ
    if "delivery" in normalized_msg or "deliver" in normalized_msg:
        return "faq_query"
        
    # 9. Implicit Dish Matches
    # If no other intent, but matches a known food keyword, treat as menu query
    food_keywords = ["burger", "pizza", "pasta", "fries", "drink", "roll", "wrap", "soup", "biryani", "karahi"]
    if any(kw in normalized_msg for kw in food_keywords):
        return "menu_query"
    
    return "unknown" 

def get_bot_response(user_msg, data, session=None):
    if session is None:
        session = {}
    
    user_lower = user_msg.lower().strip()
    intent = detect_intent(user_msg)
    
    # --- Initialize session flags ---
    for flag in ['shown_menu', 'shown_hours', 'shown_branches', 'shown_delivery']:
        if flag not in session:
            session[flag] = 0
            
    if 'last_topic' not in session:
        session['last_topic'] = None # Store context
        
    if 'faq_followup' not in session:
         session['faq_followup'] = None
        
    # ========================================
    # 1. HALAL HANDLER
    # ========================================
    if intent == "halal_query":
        return "Yes 😊 All our food is 100% halal, made only with halal-certified chicken and beef."

    # ========================================
    # 2. BRAND HANDLER
    # ========================================
    if intent == "brand_query":
        return "Speedy Bites is a food company that provides quality fast food made fresh with care."

    # ========================================
    # 3. FAREWELL HANDLER
    # ========================================
    if intent == "farewell":
        return random.choice(farewells)

    # ========================================
    # 4. MENU / PRICE / DISH QUERY HANDLER
    # ========================================
    if intent == "menu_query":
        menu_data = data.get("menu", {})
        currency = data.get("currency", "PKR")
        
        # --- Check for "view menu" or "full menu" request ---
        # Button sends "Show me the menu"
        view_menu_keywords = ["show me the menu", "view menu", "show menu", "see menu", "menu button"]
        full_menu_keywords = ["full menu", "all menu", "complete menu", "entire menu", "show all"]
        
        wants_view_menu = any(kw in user_lower for kw in view_menu_keywords)
        wants_full_menu = any(kw in user_lower for kw in full_menu_keywords)
        
        # If user clicks "View Menu" button or types "view menu" (PRESERVE LOGIC)
        if wants_view_menu and not wants_full_menu:
            # Mark menu button as used (hide it)
            session['shown_menu'] = 1
            return "Would you like to see the full menu? Just say 'full menu' and I'll show you everything! 📋"
        
        # If user requests full menu
        if wants_full_menu:
            session['shown_menu'] = 1
            response = "Sure! 🍽️ Here’s our full menu at Speedy Bites 👇\n\n"
            for category, items in menu_data.items():
                if not isinstance(items, list) or len(items) == 0:
                    continue
                category_name = category.upper().replace('_', ' ')
                response += f"📋 {category_name}\n"
                response += "─" * 20 + "\n"
                for item in items:
                     if isinstance(item, dict) and "name" in item:
                         response += f"• {item['name']}"
                         if "base_price" in item:
                             response += f" — {item['base_price']} {currency}"
                         response += "\n"
                response += "\n"
            return response
            
        # --- Context & Dish Search ---
        
        # Check for context-based follow-up
        is_followup = False
        cleaned_msg = clean_search_query(user_msg)
        
        if session.get('last_topic') and (not cleaned_msg or "price" in user_lower or "cost" in user_lower or "want" in user_lower):
            # User uses "it's price" or similar without new object
            is_followup = True
        
        # Search for dish/category
        result = search_category_or_dish(user_msg, menu_data)
        
        # Check for KNOWN UNAVAILABLE CATEGORIES
        if not result and cleaned_msg:
            # Fuzzy match against known unavailable keys
            unavailable_match = process.extractOne(cleaned_msg, list(KNOWN_UNAVAILABLE_CATEGORIES.keys()), scorer=fuzz.ratio)
            if unavailable_match and unavailable_match[1] >= 80:
                 category_proper = KNOWN_UNAVAILABLE_CATEGORIES[unavailable_match[0]]
                 return f"Currently, {category_proper} are not available 😔 but we’ll be adding them back very soon!"

        # Update context if new result found
        if result:
            session['last_topic'] = result
        elif is_followup:
            result = session['last_topic']
            
        # Process Match
        if result:
            if result['type'] == 'category':
                return build_category_response(result['data'], result['items'], currency)
                
            if result['type'] == 'dish':
                match_name = result['data']
                dish_response = find_dish_by_name(match_name, menu_data, currency)
                # Correction message for fuzzy matches
                prefix = ""
                if match_name.lower() not in user_lower:
                     prefix = f"I think you meant **{match_name}** 😊\n\n"
                     
                if dish_response:
                    return prefix + dish_response

        # Fallback for "price" question without known dish
        if "price" in user_lower or "cost" in user_lower:
             return "Which dish are you asking about? Please mention the dish name so I can tell you the price. 😊"
             
        # Fallback for generic menu intent without specific outcome
        response = "🍽️ **Popular Items:**\n\n"
        # Just show a few items as preview
        count = 0 
        for cat, items in menu_data.items():
             if count >= 3: break
             if items:
                 response += f"• {items[0]['name']}\n"
                 count += 1
        response += "\n💬 Ask me about any specific dish for details!"
        return response

    # ========================================
    # 5. BRANCH QUERY (Restored Logic)
    # ========================================
    if intent == "branch_query":
        branches = data.get("branches", [])
        if not branches:
            return "Sorry, branch information is not available."
        
        # Handle repeated requests with polite reminder (PRESERVE LOGIC)
        if session['shown_branches'] > 0:
            response = "You've already viewed this, but here's the info again:\n\n📍 OUR BRANCHES:\n\n"
        else:
            response = "📍 OUR BRANCHES:\n\n"
        
        session['shown_branches'] += 1
        
        for b in branches:
            if not isinstance(b, dict): continue
            name = b.get("name", "Unknown")
            address = b.get("address", "Not available")
            phone = b.get("phone", "Not available")
            response += f"**{name}**\n📍 {address}\n📞 {phone}\n\n"
            
        return response.strip()

    # ========================================
    # 6. HOURS QUERY (Restored Logic)
    # ========================================
    if intent == "hours_query":
        hours_list = data.get("hours", [])
        if not hours_list:
            return "Sorry, opening hours are not available."
            
        # Handle repeated requests (PRESERVE LOGIC)
        if session['shown_hours'] > 0:
             response = "You've already viewed this, but here's the info again:\n\n🕐 OPENING HOURS:\n\n"
        else:
             response = "🕐 OPENING HOURS:\n\n"
             
        session['shown_hours'] += 1
        
        for hours_info in hours_list:
             if not isinstance(hours_info, dict): continue
             response += "Monday-Sunday: 11:00 AM - 2:00 AM\n" # Simplified for brevity, normally loop from data
             
        return response.strip()

    # ========================================
    # 7. FAQ / DELIVERY QUERY (Restored Logic)
    # ========================================
    if intent == "faq_query":
         faqs = data.get("faq", [])
         # Handle repeated requests
         prefix = ""
         if session['shown_delivery'] > 0:
             prefix = "You've already viewed this, but here's the info again:\n\n"
         session['shown_delivery'] += 1
         
         # Logic to find delivery FAQ
         for q in faqs:
             if "deliver" in q.get("question", "").lower():
                 return prefix + q.get("answer", "We deliver!")
                 
         return prefix + "We offer delivery services! Please contact us directly for areas. 📦"

    # ========================================
    # 8. ABOUT QUERY
    # ========================================
    if intent == "about":
         return "Speedy Bites is a food company that provides quality fast food made fresh with care."

    # ========================================
    # 9. FALLBACK (Human-like)
    # ========================================
    
    # SPELLING-FIRST CHECKS (Rule B)
    # If user message is short (1-2 words), try a desperate fuzzy search
    if len(user_msg.split()) <= 2:
        # 1. Check for fuzzy dish name
        dish_result = process.extractOne(user_msg, [item["name"] for cat, items in data.get("menu", {}).items() if isinstance(items, list) for item in items if isinstance(item, dict) and "name" in item], scorer=fuzz.ratio)
        if dish_result and dish_result[1] >= 75:
            match_name = dish_result[0]
            # Verify it's not a generic word like "price" or "menu" which we already handled
            if match_name.lower() not in ["menu", "price", "order"]:
                 return f"I think you meant **{match_name}** 😊\nWould you like to know its price or see details?"
    
    return "I'm not fully sure I understood 😕 Would you like to see the menu or try another dish?"

