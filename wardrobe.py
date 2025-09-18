from flask import Flask, jsonify, request
from flask_cors import CORS
import random, time, re, os, joblib, base64
from datetime import datetime
from io import BytesIO
from PIL import Image
import json

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
        "comments": [],
        "created_at": "2024-01-15T10:30:00",
        "location": "Nairobi",
        "image": None
    },
    {
        "id": 2, 
        "user": "Sarah Chic", 
        "outfit": "Business casual vibes with this blazer and dark jeans combo. Ready for client meetings! 💼", 
        "stars": 4, 
        "comments": [],
        "created_at": "2024-01-15T08:45:00",
        "location": "Mombasa",
        "image": None
    },
    {
        "id": 3, 
        "user": "Mike Fresh", 
        "outfit": "Casual Friday look! Graphic tee with my favorite sneakers. Sometimes simple is best 😎", 
        "stars": 4, 
        "comments": [],
        "created_at": "2024-01-15T07:20:00",
        "location": "Kisumu",
        "image": None
    },
]

# Community discussions
discussions = [
    {
        "id": 1,
        "title": "Best Styling Tips for Kenyan Weather",
        "content": "Living in Kenya means dealing with diverse weather patterns. Here are my top tips for staying stylish while comfortable...",
        "author": "StyleGuru_KE",
        "created_at": "2024-01-15T10:00:00",
        "replies": 45,
        "category": "discussions"
    },
    {
        "id": 2,
        "title": "Where to Find Authentic Kente in Nairobi?",
        "content": "Looking for quality Kente fabric and accessories. Any recommendations for authentic shops?",
        "author": "AfricanPride",
        "created_at": "2024-01-15T07:00:00",
        "replies": 28,
        "category": "discussions"
    }
]

merchants = [
    {"id": 1, "name": "Nairobi Fashion Hub", "region": "Nairobi", "products": [
        {"name": "Classic White Tee", "icon": "👕", "category": "top", "price_band": "low"},
        {"name": "Blue Denim Jeans", "icon": "👖", "category": "bottom", "price_band": "medium"},
        {"name": "White Sneakers", "icon": "👟", "category": "shoes", "price_band": "medium"},
        {"name": "Black Blazer", "icon": "🧥", "category": "outerwear", "price_band": "high"},
        {"name": "Summer Dress", "icon": "👗", "category": "dress", "price_band": "medium"},
        {"name": "Cotton Polo", "icon": "👕", "category": "top", "price_band": "low"},
        {"name": "Khaki Chinos", "icon": "👖", "category": "bottom", "price_band": "medium"},
    ]},
    {"id": 2, "name": "Mombasa Styles", "region": "Mombasa", "products": [
        {"name": "Linen Shirt", "icon": "👕", "category": "top", "price_band": "medium"},
        {"name": "Beach Sandals", "icon": "🩴", "category": "shoes", "price_band": "low"},
        {"name": "Flowy Dress", "icon": "👗", "category": "dress", "price_band": "medium"},
        {"name": "Light Cardigan", "icon": "🧥", "category": "outerwear", "price_band": "medium"},
        {"name": "Tropical Print Shirt", "icon": "👕", "category": "top", "price_band": "medium"},
    ]},
    {"id": 3, "name": "Kisumu Collection", "region": "Kisumu", "products": [
        {"name": "Cotton Polo", "icon": "👕", "category": "top", "price_band": "low"},
        {"name": "Khaki Chinos", "icon": "👖", "category": "bottom", "price_band": "medium"},
        {"name": "Canvas Shoes", "icon": "👟", "category": "shoes", "price_band": "low"},
        {"name": "Windbreaker", "icon": "🧥", "category": "outerwear", "price_band": "medium"},
    ]},
    {"id": 4, "name": "African Heritage Store", "region": "Nairobi", "products": [
        {"name": "Traditional Kente Headband", "icon": "🎀", "category": "accessory", "price_band": "medium"},
        {"name": "Kente Print Bow Tie", "icon": "🎗️", "category": "accessory", "price_band": "low"},
        {"name": "Modern Dashiki Shirt", "icon": "👔", "category": "top", "price_band": "medium"},
        {"name": "Ankara Print Blazer", "icon": "🧥", "category": "outerwear", "price_band": "high"},
        {"name": "Maasai Beaded Necklace", "icon": "📿", "category": "accessory", "price_band": "medium"},
    ]},
]

# User locations for map feature
user_locations = [
    {"name": "Alex Style", "location": "Nairobi", "lat": -1.2921, "lng": 36.8219, "last_active": "2024-01-15T10:30:00"},
    {"name": "Sarah Chic", "location": "Mombasa", "lat": -4.0435, "lng": 39.6682, "last_active": "2024-01-15T08:45:00"},
    {"name": "Mike Fresh", "location": "Kisumu", "lat": -0.0917, "lng": 34.7680, "last_active": "2024-01-15T07:20:00"},
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

def process_image(image_data):
    """Process and validate uploaded images"""
    try:
        # Extract base64 data
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode image
        image_bytes = base64.b64decode(image_data)
        
        # Validate image size (max 5MB)
        if len(image_bytes) > 5 * 1024 * 1024:
            return None, "Image too large"
        
        # Open and validate image
        img = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large
        max_size = (800, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert back to base64
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        processed_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/jpeg;base64,{processed_data}", None
        
    except Exception as e:
        return None, f"Image processing failed: {str(e)}"

def score_outfit(items, occasion, weather, budget, style):
    score = 0
    # Occasion scoring
    if occasion == "work" and style in ["Formal", "Smart Casual"]: score += 5
    if occasion == "casual" and style in ["Casual", "Streetwear"]: score += 5
    if occasion in ["date", "event"] and style in ["Formal", "Smart Casual"]: score += 3
    if occasion == "cultural": score += 2  # New cultural occasion
    
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
        "name": "Enhanced Wardrobe AI API",
        "status": "running",
        "version": "2.0",
        "features": ["image_upload", "community_discussions", "location_map", "african_heritage"],
        "endpoints": ["/api/wardrobe", "/api/posts", "/api/dresser", "/api/shops/search", "/api/community", "/api/locations"],
        "wardrobe_items": len(wardrobe),
        "posts": len(posts),
        "discussions": len(discussions),
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
        "worn_count": 0,
        "heritage": data.get("heritage", False)  # Flag for African heritage items
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
        accessories = [i for i in wardrobe if i["category"] == "accessory"]

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
            
        # Add accessories for special occasions
        if occasion in ["date", "event", "cultural"] and accessories:
            outfit.append(random.choice(accessories))

        # Fallback if categories are missing
        if not outfit and wardrobe:
            outfit = random.sample(wardrobe, min(3, len(wardrobe)))

    outfit_str = " + ".join([f'{i["icon"]} {i["name"]}' for i in outfit])
    
    # Enhanced tips including cultural occasions
    tips = [
        "Choose colors that complement each other",
        "Layer pieces for changing weather",
        "Comfort builds confidence",
        "Accessories can elevate any outfit",
        "Fit is more important than brand",
        "Mix textures for visual interest",
        "African prints add cultural pride and uniqueness",
        "Traditional accessories tell your story",
        "Modern interpretations of cultural wear show evolution"
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
    location = data.get("location", "Nairobi")
    image_data = data.get("image")
    
    if not outfit_text:
        return jsonify({"error": "Outfit description cannot be empty"}), 400

    # Process image if provided
    processed_image = None
    if image_data:
        processed_image, error = process_image(image_data)
        if error:
            return jsonify({"error": error}), 400

    post = {
        "id": get_next_id(posts),
        "user": user_name,
        "outfit": outfit_text,
        "stars": 0,
        "comments": [],
        "created_at": datetime.now().isoformat(),
        "location": location,
        "image": processed_image
    }
    posts.append(post)
    
    # Update user location
    update_user_location(user_name, location)
    
    return jsonify(post), 201

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

@app.route("/api/community", methods=["GET", "POST"])
@rate_limit()
def community_api():
    global discussions
    if request.method == "GET":
        category = request.args.get("category", "discussions")
        filtered_discussions = [d for d in discussions if d["category"] == category]
        return jsonify({"discussions": sorted(filtered_discussions, key=lambda x: x["created_at"], reverse=True)})
    
    # POST - Create new discussion
    data = request.json or {}
    title = sanitize_text(data.get("title", "")).strip()
    content = sanitize_text(data.get("content", "")).strip()
    author = sanitize_text(data.get("author", "Anonymous")).strip()
    category = data.get("category", "discussions")
    
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400
    
    discussion = {
        "id": get_next_id(discussions),
        "title": title,
        "content": content,
        "author": author,
        "created_at": datetime.now().isoformat(),
        "replies": 0,
        "category": category
    }
    discussions.append(discussion)
    return jsonify(discussion), 201

@app.route("/api/locations", methods=["GET", "POST"])
@rate_limit()
def locations_api():
    global user_locations
    if request.method == "GET":
        # Return recent user locations for map
        return jsonify({"locations": user_locations})
    
    # POST - Update user location
    data = request.json or {}
    name = sanitize_text(data.get("name", "")).strip()
    location = data.get("location", "Nairobi")
    
    if not name:
        return jsonify({"error": "User name required"}), 400
    
    update_user_location(name, location)
    return jsonify({"message": "Location updated"}), 200

def update_user_location(name, location):
    """Update or add user location"""
    coords_map = {
        'Nairobi': {"lat": -1.2921, "lng": 36.8219},
        'Mombasa': {"lat": -4.0435, "lng": 39.6682},
        'Kisumu': {"lat": -0.0917, "lng": 34.7680},
        'Nakuru': {"lat": -0.3031, "lng": 36.0800},
        'Eldoret': {"lat": 0.5143, "lng": 35.2698}
    }
    
    coords = coords_map.get(location, coords_map['Nairobi'])
    
    # Update existing user or add new one
    existing_user = next((u for u in user_locations if u["name"] == name), None)
    if existing_user:
        existing_user["location"] = location
        existing_user["lat"] = coords["lat"]
        existing_user["lng"] = coords["lng"]
        existing_user["last_active"] = datetime.now().isoformat()
    else:
        user_locations.append({
            "name": name,
            "location": location,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "last_active": datetime.now().isoformat()
        })

@app.route("/api/shops/search", methods=["GET"])
@rate_limit()
def search_shops():
    region = request.args.get("region", "Nairobi")
    category = request.args.get("category", "")
    heritage_type = request.args.get("heritage", "")  # New parameter for heritage items
    
    results = []
    for merchant in merchants:
        # Include merchants from the specified region or heritage stores
        if merchant["region"] == region or "Heritage" in merchant["name"]:
            for product in merchant["products"]:
                # Filter by category if specified
                if category and product["category"] != category:
                    continue
                
                # Filter by heritage type if specified
                if heritage_type:
                    heritage_items = {
                        "kente": ["headband", "bow tie", "belt"],
                        "dashiki": ["dashiki", "shirt", "blouse"],
                        "ankara": ["blazer", "jacket"],
                        "jewelry": ["necklace", "bracelet", "earrings"]
                    }
                    if not any(item_type in product["name"].lower() 
                             for item_type in heritage_items.get(heritage_type, [])):
                        continue
                
                results.append({
                    **product,
                    "merchant": merchant["name"],
                    "id": len(results) + 1
                })
    
    # Shuffle results for variety
    random.shuffle(results)
    return jsonify({"results": results[:20]})  # Limit to 20 items

@app.route("/api/heritage", methods=["GET"])
@rate_limit()
def heritage_api():
    """Get African heritage fashion items"""
    category = request.args.get("category", "all")
    
    heritage_items = {
        "kente": [
            {"name": "Traditional Kente Headband", "icon": "🎀", "category": "accessory", "price_band": "medium", "merchant": "African Heritage Store"},
            {"name": "Kente Print Bow Tie", "icon": "🎗️", "category": "accessory", "price_band": "low", "merchant": "Cultural Fashion Hub"},
            {"name": "Kente Woven Belt", "icon": "🏷️", "category": "accessory", "price_band": "medium", "merchant": "Ghana Imports KE"}
        ],
        "dashiki": [
            {"name": "Modern Dashiki Shirt", "icon": "👔", "category": "top", "price_band": "medium", "merchant": "Afrocentric Styles"},
            {"name": "Dashiki Print Blouse", "icon": "👚", "category": "top", "price_band": "medium", "merchant": "Ubuntu Fashion"},
            {"name": "Contemporary Dashiki Dress", "icon": "👗", "category": "dress", "price_band": "high", "merchant": "African Elegance"}
        ],
        "ankara": [
            {"name": "Ankara Print Blazer", "icon": "🧥", "category": "outerwear", "price_band": "high", "merchant": "Ankara Couture"},
            {"name": "Ankara Business Jacket", "icon": "🧥", "category": "outerwear", "price_band": "high", "merchant": "Professional African Wear"},
            {"name": "Ankara Casual Blazer", "icon": "🧥", "category": "outerwear", "price_band": "medium", "merchant": "Modern African Fashion"}
        ],
        "jewelry": [
            {"name": "Maasai Beaded Necklace", "icon": "📿", "category": "accessory", "price_band": "medium", "merchant": "Maasai Crafts Collective"},
            {"name": "Traditional Beaded Bracelet", "icon": "💎", "category": "accessory", "price_band": "low", "merchant": "Handmade Kenya"},
            {"name": "Ethnic Beaded Earrings", "icon": "💍", "category": "accessory", "price_band": "low", "merchant": "Cultural Jewelry Store"}
        ]
    }
    
    if category == "all":
        all_items = []
        for items in heritage_items.values():
            all_items.extend(items)
        return jsonify({"heritage_items": all_items})
    
    return jsonify({"heritage_items": heritage_items.get(category, [])})

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
        "Nakuru": {"temp_c": random.randint(16, 24), "condition": "Cool"},
        "Eldoret": {"temp_c": random.randint(14, 22), "condition": "Fresh"},
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
    # Calculate comprehensive statistics
    total_items = len(wardrobe)
    categories = {}
    colors = set()
    price_bands = {"low": 0, "medium": 0, "high": 0}
    heritage_count = 0
    
    for item in wardrobe:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        colors.add(item.get("color", "neutral"))
        price_bands[item.get("price_band", "medium")] += 1
        if item.get("heritage", False):
            heritage_count += 1
    
    # Calculate community stats
    total_discussions = len(discussions)
    total_replies = sum(d.get("replies", 0) for d in discussions)
    
    return jsonify({
        "wardrobe": {
            "total_items": total_items,
            "categories": categories,
            "unique_colors": len(colors),
            "price_distribution": price_bands,
            "heritage_items": heritage_count
        },
        "social": {
            "total_posts": len(posts),
            "avg_post_stars": sum(p.get("stars", 0) for p in posts) / max(len(posts), 1),
            "posts_with_images": len([p for p in posts if p.get("image")])
        },
        "community": {
            "total_discussions": total_discussions,
            "total_replies": total_replies,
            "active_users": len(user_locations)
        },
        "locations": {
            "active_cities": len(set(u["location"] for u in user_locations)),
            "total_users_mapped": len(user_locations)
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(413)
def payload_too_large(error):
    return jsonify({"error": "File too large. Maximum size is 5MB"}), 413

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("🚀 Starting Enhanced Wardrobe AI Server...")
    print("📱 Frontend: Save index.html and open in browser")
    print("🔗 API Base: http://127.0.0.1:5000")
    print("✅ CORS enabled for frontend connection")
    print("🤖 ML Model:", "Loaded" if model else "Not found (using fallback logic)")
    print("📸 Image upload: Enabled (max 5MB)")
    print("🗺️  Location tracking: Enabled")
    print("👥 Community features: Enabled")
    print("🌍 African heritage items: Available")
    print("\n📋 Available endpoints:")
    print("  GET  /                     - API status and features")
    print("  GET  /api/wardrobe         - Get wardrobe items") 
    print("  POST /api/wardrobe         - Add wardrobe item")
    print("  GET  /api/posts            - Get social posts")
    print("  POST /api/posts            - Create new post (with image support)")
    print("  POST /api/posts/{id}/rate  - Rate a post (stars only)")
    print("  GET  /api/dresser          - Get AI outfit suggestion")
    print("  GET  /api/shops/search     - Search shop items")
    print("  GET  /api/community        - Get community discussions")
    print("  POST /api/community        - Create new discussion")
    print("  GET  /api/locations        - Get user locations for map")
    print("  POST /api/locations        - Update user location")
    print("  GET  /api/heritage         - Get African heritage items")
    print("  GET  /api/weather          - Get weather data")
    print("  GET  /api/stats            - Get comprehensive app statistics")
    print("\n🎯 Enhanced features ready:")
    print("  📸 Real image uploads (processed and optimized)")
    print("  🌍 African heritage fashion categories")
    print("  👥 Community discussions and challenges")
    print("  🗺️  User location mapping")
    print("  ⭐ Stars-only rating system")
    print("  🔍 Enhanced search and filtering")
    print("\n🎉 Ready to serve requests!")
    
    # Configure max content length for file uploads
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max request size
    
    app.run(debug=True, host="127.0.0.1", port=5000)
