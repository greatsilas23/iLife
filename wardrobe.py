from flask import Flask, jsonify, request
from flask_cors import CORS
import random, time, re, os, joblib
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Data stores
wardrobe = []
posts = [
    {
        "id": 1, 
        "user": "Alex Style", 
        "outfit": "Perfect summer dress with white sneakers for brunch! Feeling confident and comfy 💫", 
        "stars": 5, 
        "likes": 127, 
        "comments": [],
        "created_at": "2024-01-15T10:30:00"
    },
    {
        "id": 2, 
        "user": "Sarah Chic", 
        "outfit": "Business casual vibes with this blazer and dark jeans combo. Ready for client meetings! 💼", 
        "stars": 4, 
        "likes": 89, 
        "comments": [],
        "created_at": "2024-01-15T08:45:00"
    },
    {
        "id": 3, 
        "user": "Mike Fresh", 
        "outfit": "Casual Friday look! Graphic tee with my favorite sneakers. Sometimes simple is best 😎", 
        "stars": 4, 
        "likes": 156, 
        "comments": [],
        "created_at": "2024-01-15T07:20:00"
    },
]

merchants = [
    {"id": 1, "name": "Nairobi Fashion Hub", "region": "Nairobi", "products": [
        {"name": "Classic White Tee", "icon": "👕", "category": "top", "price_band": "low"},
        {"name": "Blue Denim Jeans", "icon": "👖", "category": "bottom", "price_band": "medium"},
        {"name": "White Sneakers", "icon": "👟", "category": "shoes", "price_band": "medium"},
        {"name": "Black Blazer", "icon": "🧥", "category": "outerwear", "price_band": "high"},
        {"name": "Summer Dress", "icon": "👗", "category": "dress", "price_band": "medium"},
    ]},
    {"id": 2, "name": "Mombasa Styles", "region": "Mombasa", "products": [
        {"name": "Linen Shirt", "icon": "👕", "category": "top", "price_band": "medium"},
        {"name": "Beach Sandals", "icon": "🩴", "category": "shoes", "price_band": "low"},
        {"name": "Flowy Dress", "icon": "👗", "category": "dress", "price_band": "medium"},
        {"name": "Light Cardigan", "icon": "🧥", "category": "outerwear", "price_band": "medium"},
    ]},
    {"id": 3, "name": "Kisumu Collection", "region": "Kisumu", "products": [
        {"name": "Cotton Polo", "icon": "👕", "category": "top", "price_band": "low"},
        {"name": "Khaki Chinos", "icon": "👖", "category": "bottom", "price_band": "medium"},
        {"name": "Canvas Shoes", "icon": "👟", "category": "shoes", "price_band": "low"},
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
if os.path.exists("outfit_rf_model.joblib"):
    try:
        model = joblib.load("outfit_rf_model.joblib")
        print("✅ ML model loaded successfully.")
    except Exception as e:
        print("⚠️ Could not load outfit_rf_model.joblib:", e)

# Simple rate limiting
rate_log = {}
BAD_WORDS = {"shit", "fuck", "damn", "bitch"}
BAD_WORDS_RE = re.compile(r"|".join([re.escape(w) for w in BAD_WORDS]), re.IGNORECASE)

# Helper functions
def rate_limit(max_calls=50, window=60):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            key = request.remote_addr
            now = time.time()
            history = rate_log.get(key, [])
            history = [t for t in history if now - t < window]
            if len(history) >= max_calls:
                return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
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

def score_outfit(items, occasion, weather, budget, style):
    score = 0
    # Occasion scoring
    if occasion == "work" and style in ["Formal", "Smart Casual"]: score += 5
    if occasion == "casual" and style in ["Casual", "Streetwear"]: score += 5
    if occasion in ["date", "event"] and style in ["Formal", "Smart Casual"]: score += 3
    
    # Weather scoring
    if weather == "hot" and any(i["category"] in ["dress", "top"] for i in items): score += 3
    if weather == "cool" and any(i["category"] == "outerwear" for i in items): score += 3
    
    # Budget scoring
    if any(i["price_band"] == budget for i in items): score += 2
    return score

# === ROUTES ===

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "Wardrobe AI API",
        "status": "running",
        "version": "1.0",
        "endpoints": ["/api/wardrobe", "/api/posts", "/api/dresser", "/api/shops/search", "/api/profile"],
        "wardrobe_items": len(wardrobe),
        "posts": len(posts),
        "ml_model_loaded": bool(model)
    })

@app.route("/api/wardrobe", methods=["GET", "POST"])
@rate_limit()
def wardrobe_api():
    global wardrobe
    if request.method == "GET":
        return jsonify({"wardrobe": sorted(wardrobe, key=lambda x: x.get("id", 0), reverse=True)})

    # POST - Add new item
    data = request.json or {}
    name = sanitize_text(data.get("name", "")).strip()
    
    if not name or len(name) < 2:
        return jsonify({"error": "Item name must be at least 2 characters long"}), 400
    
    if any(w["name"].lower() == name.lower() for w in wardrobe):
        return jsonify({"error": "Item with this name already exists"}), 400

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
    
    return jsonify({"message": "Item deleted successfully"}), 200

@app.route("/api/dresser", methods=["GET"])
@rate_limit()
def ai_dresser():
    if not wardrobe:
        return jsonify({
            "outfit": "Add some clothes to your wardrobe first! 👔",
            "tip": "Build your wardrobe to get personalized AI suggestions."
        })

    occasion = request.args.get("occasion", "casual")
    temp_c = request.args.get("temp_c", type=float)
    weather = temp_to_band(temp_c)
    budget = request.args.get("budget", profile["budget"])
    style = profile["style"]

    outfit = []

    # Try ML model first
    if model:
        try:
            names = [item["name"] for item in wardrobe]
            preds = model.predict(names)
            categories = list(zip(names, preds))

            # Pick items based on model predictions
            top = next((wardrobe[i] for i, (_, c) in enumerate(categories) if c == "top"), None)
            bottom = next((wardrobe[i] for i, (_, c) in enumerate(categories) if c == "bottom"), None)
            shoes = next((wardrobe[i] for i, (_, c) in enumerate(categories) if c == "shoes"), None)

            if top: outfit.append(top)
            if bottom: outfit.append(bottom)
            if shoes: outfit.append(shoes)

        except Exception as e:
            print(f"⚠️ ML model prediction failed: {e}")

    # Fallback rule-based selection
    if not outfit:
        # Categorize items
        tops = [i for i in wardrobe if i["category"] == "top"]
        bottoms = [i for i in wardrobe if i["category"] == "bottom"]
        dresses = [i for i in wardrobe if i["category"] == "dress"]
        shoes = [i for i in wardrobe if i["category"] == "shoes"]
        outerwear = [i for i in wardrobe if i["category"] == "outerwear"]

        # Choose outfit based on occasion and weather
        if dresses and random.random() < 0.3:
            outfit.append(random.choice(dresses))
            if shoes: outfit.append(random.choice(shoes))
        else:
            if tops: outfit.append(random.choice(tops))
            if bottoms: outfit.append(random.choice(bottoms))
            if shoes: outfit.append(random.choice(shoes))

        # Add outerwear for cool weather or formal occasions
        if (weather in ["cool", "mild"] or occasion in ["work", "event"]) and outerwear:
            outfit.append(random.choice(outerwear))

        # Fallback if categories are missing
        if not outfit and wardrobe:
            outfit = random.sample(wardrobe, min(3, len(wardrobe)))

    outfit_str = " + ".join([f'{i["icon"]} {i["name"]}' for i in outfit])
    
    tips = [
        "Choose colors that complement each other",
        "Layer pieces for changing weather",
        "Comfort builds confidence",
        "Accessories can elevate any outfit",
        "Fit is more important than brand",
        "Mix textures for visual interest"
    ]

    return jsonify({
        "outfit": outfit_str,
        "tip": random.choice(tips),
        "weather": weather,
        "occasion": occasion
    })

@app.route("/api/posts", methods=["GET", "POST"])
@rate_limit()
def posts_api():
    global posts
    if request.method == "GET":
        return jsonify({"posts": sorted(posts, key=lambda x: x.get("created_at", ""), reverse=True)})

    # POST - Create new post
    data = request.json or {}
    outfit_text = sanitize_text(data.get("outfit", "")).strip()
    user_name = sanitize_text(data.get("user", "Anonymous")).strip()
    
    if not outfit_text:
        return jsonify({"error": "Outfit description cannot be empty"}), 400

    post = {
        "id": get_next_id(posts),
        "user": user_name,
        "outfit": outfit_text,
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
    return jsonify({"message": "Post liked!", "likes": post["likes"]})

@app.route("/api/posts/<int:post_id>/rate", methods=["POST"])
@rate_limit()
def rate_post(post_id):
    global posts
    data = request.json or {}
    stars = min(5, max(1, data.get("stars", 5)))  # Ensure stars are between 1-5
    
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    post["stars"] = stars
    return jsonify({"message": f"Rated {stars} stars!", "stars": post["stars"]})

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
    
    # Shuffle results for variety
    random.shuffle(results)
    return jsonify({"results": results[:12]})  # Limit to 12 items

@app.route("/api/profile", methods=["GET", "POST"])
@rate_limit()
def profile_api():
    global profile
    if request.method == "GET":
        return jsonify(profile)
    
    # POST - Update profile
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
    # Mock weather data for Kenyan cities
    weather_data = {
        "Nairobi": {"temp_c": random.randint(18, 26), "condition": "Partly Cloudy"},
        "Mombasa": {"temp_c": random.randint(25, 32), "condition": "Sunny"},
        "Kisumu": {"temp_c": random.randint(20, 28), "condition": "Cloudy"},
    }
    
    city_weather = weather_data.get(city, {"temp_c": 24, "condition": "Fair"})
    return jsonify({
        "city": city,
        "temp_c": city_weather["temp_c"],
        "condition": city_weather["condition"]
    })

@app.route("/api/stats", methods=["GET"])
@rate_limit()
def stats_api():
    # Calculate wardrobe statistics
    total_items = len(wardrobe)
    categories = {}
    colors = set()
    price_bands = {"low": 0, "medium": 0, "high": 0}
    
    for item in wardrobe:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        colors.add(item.get("color", "neutral"))
        price_bands[item.get("price_band", "medium")] += 1
    
    return jsonify({
        "total_items": total_items,
        "categories": categories,
        "unique_colors": len(colors),
        "price_distribution": price_bands,
        "total_posts": len(posts),
        "avg_post_likes": sum(p.get("likes", 0) for p in posts) / max(len(posts), 1)
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("🚀 Starting Wardrobe AI Server...")
    print("📱 Frontend: Save index.html and open in browser")
    print("🔗 API Base: http://127.0.0.1:5000")
    print("✅ CORS enabled for frontend connection")
    print("🤖 ML Model:", "Loaded" if model else "Not found (using fallback logic)")
    print("\n📋 Available endpoints:")
    print("  GET  /                     - API status")
    print("  GET  /api/wardrobe         - Get wardrobe items") 
    print("  POST /api/wardrobe         - Add wardrobe item")
    print("  GET  /api/posts            - Get social posts")
    print("  POST /api/posts            - Create new post")
    print("  GET  /api/dresser          - Get AI outfit suggestion")
    print("  GET  /api/shops/search     - Search shop items")
    print("  GET  /api/stats            - Get app statistics")
    print("\n🎯 Ready to serve requests!")
    
    app.run(debug=True, host="127.0.0.1", port=5000)