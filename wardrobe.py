from flask import Flask, jsonify, request
from flask_cors import CORS
import random, time, re, os, joblib
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

# Try loading trained model
model = None
if os.path.exists("model.pkl"):
    try:
        model = joblib.load("model.pkl")
        print("✅ ML model loaded successfully.")
    except Exception as e:
        print("⚠️ Could not load model.pkl:", e)

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

# Outfit scoring (unchanged)
def score_outfit(items, occasion, weather, budget, style):
    score = 0
    if occasion == "work" and style in ["Formal", "Smart Casual"]: score += 5
    if occasion == "casual" and style in ["Casual", "Streetwear"]: score += 5
    if occasion in ["date", "wedding"] and style in ["Formal", "Smart Casual"]: score += 3
    if weather == "hot" and any(i["category"] in ["dress", "top"] for i in items): score += 3
    if weather == "cool" and any(i["category"] == "outerwear" for i in items): score += 3
    if any(i["price_band"] == budget for i in items): score += 2
    return score

# --- ROUTES ---

@app.route("/api/wardrobe", methods=["GET", "POST"])
@rate_limit()
def wardrobe_api():
    global wardrobe
    if request.method == "GET":
        return jsonify({"wardrobe": sorted(wardrobe, key=lambda x: x["id"], reverse=True)})

    data = request.json or {}
    name = sanitize_text(data.get("name", "")).strip()
    if not name or len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters"}), 400
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

    outfit = []

    if model:
        try:
            # Convert wardrobe items into model-friendly text
            names = [item["name"] for item in wardrobe]
            preds = model.predict(names)  # expects model trained on item names
            categories = list(zip(names, preds))

            # Pick one top, one bottom, one shoes if available
            top = next((wardrobe[i] for i, (_, c) in enumerate(categories) if c == "top"), None)
            bottom = next((wardrobe[i] for i, (_, c) in enumerate(categories) if c == "bottom"), None)
            shoes = next((wardrobe[i] for i, (_, c) in enumerate(categories) if c == "shoes"), None)

            if top: outfit.append(top)
            if bottom: outfit.append(bottom)
            if shoes: outfit.append(shoes)

        except Exception as e:
            print("⚠️ Model prediction failed:", e)

    # Fallback if no AI suggestion
    if not outfit:
        tops = [i for i in wardrobe if i["category"] == "top"]
        bottoms = [i for i in wardrobe if i["category"] == "bottom"]
        dresses = [i for i in wardrobe if i["category"] == "dress"]
        shoes = [i for i in wardrobe if i["category"] == "shoes"]
        outerwear = [i for i in wardrobe if i["category"] == "outerwear"]

        if dresses and random.random() < 0.4:
            outfit.append(random.choice(dresses))
            if shoes: outfit.append(random.choice(shoes))
        else:
            if tops: outfit.append(random.choice(tops))
            if bottoms: outfit.append(random.choice(bottoms))
            if shoes: outfit.append(random.choice(shoes))
        if (weather == "cool" or occasion in ["work", "wedding"]) and outerwear:
            outfit.append(random.choice(outerwear))
        if not outfit:
            outfit = random.sample(wardrobe, min(2, len(wardrobe)))

    outfit_str = " + ".join([f'{i["icon"]} {i["name"]}' for i in outfit])
    tips = ["Match colors thoughtfully", "Layer for weather changes", "Comfort is key", "Confidence makes any outfit better"]

    return jsonify({
        "outfit": outfit_str,
        "tip": random.choice(tips)
    })

# Additional routes for explore, shops, posts, profile, weather, etc.
@app.route("/api/explore", methods=["GET"])
@rate_limit()
def explore_api():
    return jsonify({"explore": explore_items})

@app.route("/api/posts", methods=["GET", "POST"])
@rate_limit()
def posts_api():
    global posts
    if request.method == "GET":
        return jsonify({"posts": sorted(posts, key=lambda x: x["id"], reverse=True)})
    
    data = request.json or {}
    post = {
        "id": get_next_id(posts),
        "user": sanitize_text(data.get("user", "Anonymous")),
        "outfit": sanitize_text(data.get("outfit", "")),
        "stars": 0,
        "likes": 0,
        "comments": [],
        "created_at": datetime.now().isoformat()
    }
    posts.append(post)
    return jsonify(post), 201

@app.route("/api/posts/<int:post_id>/like", methods=["POST"])
@rate_limit()
def like_post(post_id):
    global posts
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    post["likes"] = post.get("likes", 0) + 1
    return jsonify({"message": "Liked", "likes": post["likes"]})

@app.route("/api/posts/<int:post_id>/rate", methods=["POST"])
@rate_limit()
def rate_post(post_id):
    global posts
    data = request.json or {}
    stars = data.get("stars", 5)
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    post["stars"] = stars
    return jsonify({"message": "Rated", "stars": post["stars"]})

@app.route("/api/shops/search", methods=["GET"])
@rate_limit()
def search_shops():
    region = request.args.get("region", "Nairobi")
    category = request.args.get("category", "")
    
    results = []
    for merchant in merchants:
        if merchant["region"] == region:
            for product in merchant["products"]:
                if not category or product["category"] == category:
                    results.append({
                        **product,
                        "merchant": merchant["name"],
                        "id": len(results) + 1
                    })
    
    return jsonify({"results": results})

@app.route("/api/profile", methods=["GET", "POST"])
@rate_limit()
def profile_api():
    global profile
    if request.method == "GET":
        return jsonify(profile)
    
    data = request.json or {}
    profile.update({
        "user": sanitize_text(data.get("user", profile["user"])),
        "location": data.get("location", profile["location"]),
        "style": data.get("style", profile["style"]),
        "budget": data.get("budget", profile["budget"])
    })
    return jsonify(profile)

@app.route("/api/weather", methods=["GET"])
@rate_limit()
def weather_api():
    city = request.args.get("city", "Nairobi")
    # Mock weather data
    temps = {"Nairobi": 22, "Mombasa": 28, "Kisumu": 25}
    return jsonify({
        "city": city,
        "temp_c": temps.get(city, 24),
        "condition": "Partly Cloudy"
    })

# Health check
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "Wardrobe AI API",
        "status": "running",
        "items": len(wardrobe),
        "posts": len(posts),
        "ml_model": bool(model)
    })

if __name__ == "__main__":
    print("🚀 Starting Wardrobe AI...")
    print("📱 Open: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)