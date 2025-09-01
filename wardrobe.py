from flask import Flask, jsonify, request
from flask_cors import CORS
import random, time, re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Data stores
wardrobe = []
explore_items = [
    {"id": 1, "name": "White Tee", "icon": "👕", "category": "top", "color": "white", "price_band": "low"},
    {"id": 2, "name": "Blue Jeans", "icon": "👖", "category": "bottom", "color": "blue", "price_band": "medium"},
    {"id": 3, "name": "Summer Dress", "icon": "👗", "category": "dress", "color": "red", "price_band": "medium"},
    {"id": 4, "name": "Denim Jacket", "icon": "🧥", "category": "outerwear", "color": "blue", "price_band": "medium"},
    {"id": 5, "name": "White Sneakers", "icon": "👟", "category": "shoes", "color": "white", "price_band": "low"},
    {"id": 6, "name": "Black Blazer", "icon": "🧥", "category": "outerwear", "color": "black", "price_band": "high"},
    {"id": 7, "name": "Chinos", "icon": "👖", "category": "bottom", "color": "beige", "price_band": "medium"},
    {"id": 8, "name": "Silk Blouse", "icon": "👕", "category": "top", "color": "white", "price_band": "high"},
]

posts = [
    {"id": 1, "user": "Alice", "outfit": "👗 Red dress with 👟 white sneakers", "stars": 5, "likes": 12, "comments": []},
    {"id": 2, "user": "Bob", "outfit": "👕 Blue shirt and 👖 black jeans", "stars": 4, "likes": 8, "comments": []},
]

merchants = [
    {"id": 1, "name": "Nairobi Fashion", "region": "Nairobi", "products": [
        {"name": "Graphic Tee", "icon": "👕", "category": "top", "price_band": "low"},
        {"name": "Classic Jeans", "icon": "👖", "category": "bottom", "price_band": "medium"},
        {"name": "Sneakers", "icon": "👟", "category": "shoes", "price_band": "low"},
    ]},
    {"id": 2, "name": "Mombasa Styles", "region": "Mombasa", "products": [
        {"name": "Linen Shirt", "icon": "👕", "category": "top", "price_band": "medium"},
        {"name": "Beach Sandals", "icon": "🩴", "category": "shoes", "price_band": "low"},
    ]},
]

profile = {
    "user": "Fashion Lover",
    "location": "Nairobi",
    "currency": "KES",
    "style": "Casual",
    "budget": "medium",
}

# Simple rate limiting
rate_log = {}
BAD_WORDS = {"shit", "fuck", "damn"}
BAD_WORDS_RE = re.compile(r"|".join([re.escape(w) for w in BAD_WORDS]), re.IGNORECASE)

# Helpers
def rate_limit(max_calls=20, window=60):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            key = request.remote_addr
            now = time.time()
            history = rate_log.get(key, [])
            history = [t for t in history if now - t < window]
            if len(history) >= max_calls:
                return jsonify({"error": "Rate limit exceeded"}), 429
            history.append(now)
            rate_log[key] = history
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

def sanitize_text(text):
    if not text: return text
    return BAD_WORDS_RE.sub("***", text) if BAD_WORDS_RE.search(text) else text

def get_next_id(items):
    return max([i["id"] for i in items], default=0) + 1

def temp_to_band(temp_c):
    if temp_c is None: return "mild"
    if temp_c >= 28: return "hot"
    if temp_c >= 22: return "warm"
    if temp_c >= 16: return "mild"
    return "cool"

# Optimized outfit scoring
def score_outfit(items, occasion, weather, budget, style):
    score = 0
    
    # Occasion match
    if occasion == "work" and style in ["Formal", "Smart Casual"]: score += 5
    if occasion == "casual" and style in ["Casual", "Streetwear"]: score += 5
    if occasion in ["date", "wedding"] and style in ["Formal", "Smart Casual"]: score += 3
    
    # Weather match
    if weather == "hot" and any(i["category"] in ["dress", "top"] for i in items): score += 3
    if weather == "cool" and any(i["category"] == "outerwear" for i in items): score += 3
    
    # Budget match
    if any(i["price_band"] == budget for i in items): score += 2
    
    return score

# API Routes
@app.route("/api/wardrobe", methods=["GET", "POST"])
@rate_limit()
def wardrobe_api():
    global wardrobe
    
    if request.method == "GET":
        return jsonify({"wardrobe": sorted(wardrobe, key=lambda x: x["id"], reverse=True)})
    
    # POST
    data = request.json or {}
    name = sanitize_text(data.get("name", "")).strip()
    
    if not name or len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters"}), 400
    
    # Check duplicates
    if any(w["name"].lower() == name.lower() for w in wardrobe):
        return jsonify({"error": "Item already exists"}), 400
    
    item = {
        "id": get_next_id(wardrobe),
        "name": name,
        "icon": data.get("icon", "👕"),
        "category": data.get("category", "top"),
        "color": data.get("color", "neutral"),
        "price_band": data.get("price_band", "medium"),
        "added_date": datetime.now().isoformat(),
        "worn_count": 0
    }
    
    wardrobe.append(item)
    return jsonify(item), 201

@app.route("/api/wardrobe/<int:item_id>", methods=["DELETE"])
@rate_limit()
def delete_wardrobe_item(item_id):
    global wardrobe
    initial_len = len(wardrobe)
    wardrobe = [i for i in wardrobe if i["id"] != item_id]
    
    if len(wardrobe) == initial_len:
        return jsonify({"error": "Item not found"}), 404
    
    return jsonify({"message": "Deleted"}), 200

@app.route("/api/dresser", methods=["GET"])
@rate_limit()
def ai_dresser():
    if not wardrobe:
        return jsonify({
            "outfit": "Add clothes first! 👔",
            "tip": "Build your wardrobe to get AI suggestions."
        })
    
    occasion = request.args.get("occasion", "casual")
    temp_c = request.args.get("temp_c", type=float)
    weather = temp_to_band(temp_c)
    budget = request.args.get("budget", profile["budget"])
    style = profile["style"]
    
    # Get items by category
    tops = [i for i in wardrobe if i["category"] == "top"]
    bottoms = [i for i in wardrobe if i["category"] == "bottom"]
    dresses = [i for i in wardrobe if i["category"] == "dress"]
    shoes = [i for i in wardrobe if i["category"] == "shoes"]
    outerwear = [i for i in wardrobe if i["category"] == "outerwear"]
    
    # Simple outfit generation
    outfit = []
    
    # Try dress first
    if dresses and random.random() < 0.4:
        outfit.append(random.choice(dresses))
        if shoes: outfit.append(random.choice(shoes))
    else:
        # Top + bottom combination
        if tops: outfit.append(random.choice(tops))
        if bottoms: outfit.append(random.choice(bottoms))
        if shoes: outfit.append(random.choice(shoes))
    
    # Add jacket for cool weather or formal occasions
    if (weather == "cool" or occasion in ["work", "wedding"]) and outerwear:
        outfit.append(random.choice(outerwear))
    
    if not outfit:
        outfit = random.sample(wardrobe, min(2, len(wardrobe)))
    
    outfit_str = " + ".join([f'{i["icon"]} {i["name"]}' for i in outfit])
    
    tips = [
        "Match colors thoughtfully",
        "Layer for weather changes",
        "Comfort is key",
        "Confidence makes any outfit better"
    ]
    
    return jsonify({
        "outfit": outfit_str,
        "tip": random.choice(tips)
    })

@app.route("/api/explore", methods=["GET"])
@rate_limit()
def get_explore():
    # Simple personalization
    user_budget = profile["budget"]
    recommended = []
    
    for item in explore_items:
        item_copy = item.copy()
        if item["price_band"] == user_budget:
            item_copy["recommended"] = True
        recommended.append(item_copy)
    
    return jsonify({"explore": recommended})

@app.route("/api/shops/search", methods=["GET"])
@rate_limit()
def shop_search():
    region = request.args.get("region", profile["location"])
    category = request.args.get("category", "")
    
    results = []
    for merchant in merchants:
        if merchant["region"] != region:
            continue
        for product in merchant["products"]:
            if category and product["category"] != category:
                continue
            results.append({**product, "merchant": merchant["name"], "region": merchant["region"]})
    
    return jsonify({"results": results})

@app.route("/api/shops/add-to-wardrobe", methods=["POST"])
@rate_limit()
def shop_add():
    data = request.json or {}
    name = sanitize_text(data.get("name", "")).strip()
    
    if not name:
        return jsonify({"error": "Name required"}), 400
    
    item = {
        "id": get_next_id(wardrobe),
        "name": name,
        "icon": data.get("icon", "🛍️"),
        "category": data.get("category", "top"),
        "color": "neutral",
        "price_band": data.get("price_band", "medium"),
        "added_date": datetime.now().isoformat(),
        "worn_count": 0
    }
    
    wardrobe.append(item)
    return jsonify(item), 201

@app.route("/api/posts", methods=["GET", "POST"])
@rate_limit()
def posts_api():
    global posts
    
    if request.method == "GET":
        return jsonify({"posts": sorted(posts, key=lambda p: p["id"], reverse=True)})
    
    # POST
    data = request.json or {}
    user = sanitize_text(data.get("user", "User")).strip()
    outfit = sanitize_text(data.get("outfit", "")).strip()
    
    if not outfit:
        return jsonify({"error": "Outfit description required"}), 400
    
    post = {
        "id": get_next_id(posts),
        "user": user,
        "outfit": outfit,
        "stars": 0,
        "likes": 0,
        "comments": []
    }
    
    posts.append(post)
    return jsonify(post), 201

@app.route("/api/posts/<int:post_id>/like", methods=["POST"])
@rate_limit()
def like_post(post_id):
    for post in posts:
        if post["id"] == post_id:
            post["likes"] += 1
            return jsonify({"likes": post["likes"]})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/posts/<int:post_id>/rate", methods=["POST"])
@rate_limit()
def rate_post(post_id):
    data = request.json or {}
    stars = int(data.get("stars", 0))
    
    if not 1 <= stars <= 5:
        return jsonify({"error": "Stars must be 1-5"}), 400
    
    for post in posts:
        if post["id"] == post_id:
            post["stars"] = max(post.get("stars", 0), stars)
            return jsonify({"stars": post["stars"]})
    
    return jsonify({"error": "Not found"}), 404

@app.route("/api/profile", methods=["GET", "POST"])
@rate_limit()
def user_profile():
    global profile
    
    if request.method == "GET":
        return jsonify(profile)
    
    # POST - update profile
    data = request.json or {}
    for field in ["user", "location", "style", "budget"]:
        if field in data and data[field].strip():
            profile[field] = data[field].strip()
    
    # Update currency based on location
    profile["currency"] = "KES"  # All Kenyan cities use KES
    
    return jsonify(profile)

@app.route("/api/weather", methods=["GET"])
@rate_limit()
def weather():
    city = request.args.get("city", profile["location"])
    
    # Simple temperature simulation based on city
    temps = {"Nairobi": 22, "Mombasa": 28, "Kisumu": 25, "Nakuru": 20, "Eldoret": 18}
    base_temp = temps.get(city, 24)
    current_temp = round(base_temp + random.uniform(-3, 5), 1)
    
    conditions = ["Partly cloudy", "Sunny", "Overcast", "Pleasant"]
    
    return jsonify({
        "city": city,
        "temp_c": current_temp,
        "summary": random.choice(conditions)
    })

@app.route("/api/export/wardrobe", methods=["GET"])
@rate_limit()
def export_wardrobe():
    return jsonify({
        "profile": profile,
        "wardrobe": wardrobe,
        "export_date": datetime.now().isoformat(),
        "version": "2.0"
    })

@app.route("/api/style/match", methods=["POST"])
@rate_limit()
def find_matches():
    data = request.json or {}
    item_id = data.get("item_id")
    
    target = next((item for item in wardrobe if item["id"] == item_id), None)
    if not target:
        return jsonify({"error": "Item not found"}), 404
    
    # Simple color matching
    color_matches = {
        "white": ["black", "blue", "red"],
        "black": ["white", "red", "pink"],
        "blue": ["white", "beige", "neutral"],
        "red": ["white", "black", "neutral"],
        "neutral": ["white", "black", "blue"]
    }
    
    good_colors = color_matches.get(target["color"], ["neutral"])
    matches = [item for item in wardrobe 
              if item["id"] != item_id and 
              (item["color"] in good_colors or item["category"] != target["category"])]
    
    return jsonify({"matches": matches[:5], "target_item": target})

# Health check
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "Wardrobe AI API",
        "status": "running",
        "items": len(wardrobe),
        "posts": len(posts)
    })

if __name__ == "__main__":
    print("🚀 Starting Wardrobe AI...")
    print("📱 Open: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)