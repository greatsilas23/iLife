from flask import Flask, jsonify, request
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)

# Mock databases
wardrobe = []
explore_items = [
    {"id": 1, "name": "Casual Shirt", "icon": "👕"},
    {"id": 2, "name": "Jeans", "icon": "👖"},
    {"id": 3, "name": "Summer Dress", "icon": "👗"},
    {"id": 4, "name": "Hoodie", "icon": "🧥"},
    {"id": 5, "name": "Sneakers", "icon": "👟"}
]
posts = [
    {"id": 1, "user": "Alice", "outfit": "👗 Red Dress with 👟 Sneakers"},
    {"id": 2, "user": "Bob", "outfit": "👕 Blue Shirt and 👖 Black Jeans"}
]

# --- Wardrobe Endpoints ---
@app.route("/api/wardrobe", methods=["GET"])
def get_wardrobe():
    return jsonify({"wardrobe": wardrobe})

@app.route("/api/wardrobe", methods=["POST"])
def add_wardrobe_item():
    data = request.json
    item_id = len(wardrobe) + 1
    item = {"id": item_id, "name": data["name"], "icon": data["icon"]}
    wardrobe.append(item)
    return jsonify(item), 201

@app.route("/api/wardrobe/<int:item_id>", methods=["DELETE"])
def delete_wardrobe_item(item_id):
    global wardrobe
    wardrobe = [i for i in wardrobe if i["id"] != item_id]
    return jsonify({"message": "Deleted"}), 200

# --- AI Dresser Endpoint ---
@app.route("/api/dresser", methods=["GET"])
def ai_dresser():
    if not wardrobe:
        return jsonify({"outfit": "No clothes yet!", "tip": "Add more to your wardrobe."})
    outfit = random.sample(wardrobe, min(len(wardrobe), 2))
    outfit_names = " + ".join([f'{i["icon"]} {i["name"]}' for i in outfit])
    tip = random.choice([
        "Match colors smartly!",
        "Don’t forget shoes.",
        "Layering makes outfits stylish.",
        "Confidence is the best outfit!"
    ])
    return jsonify({"outfit": outfit_names, "tip": tip})

# --- Explore Endpoint ---
@app.route("/api/explore", methods=["GET"])
def get_explore():
    return jsonify({"explore": explore_items})

# --- For You (Posts) ---
@app.route("/api/posts", methods=["GET"])
def get_posts():
    return jsonify({"posts": posts})

@app.route("/api/posts", methods=["POST"])
def add_post():
    data = request.json
    post_id = len(posts) + 1
    post = {"id": post_id, "user": data["user"], "outfit": data["outfit"]}
    posts.append(post)
    return jsonify(post), 201

if __name__ == "__main__":
    app.run(debug=True)
