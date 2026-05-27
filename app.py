"""
VISCOM Instagram Profile Analyzer
Flask application — serves the dashboard and API.
"""

import json
import os
import sys
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())

# Import after path is set
from lib.scraper import InstagramScraper
from lib.analyzer import ContentAnalyzer

# Cache for recent analyses
analysis_cache = {}


def generate_demo_data(username: str) -> dict:
    """Generate realistic demo analysis data so the UI can be viewed immediately."""
    random.seed(hash(username) % 10000)

    followers = random.choice([1200, 3400, 8900, 15000, 42000, 87000, 150000, 320000, 580000, 1200000])
    following = int(followers * random.uniform(0.05, 0.4))
    post_count = random.randint(50, 800)
    is_verified = followers > 50000
    is_business = random.choice([True, True, False])

    bios = [
        f"Creative storyteller | {random.choice(['NYC', 'LA', 'London', 'Paris'])} 📍",
        f"{random.choice(['Photographer', 'Creator', 'Designer', 'Coach', 'Founder'])} ✨ Helping you {random.choice(['grow', 'create', 'build', 'inspire', 'transform'])}",
        f"Building @{username} 🚀 | {random.choice(['DM for collabs', 'Link below 👇', 'Content creator', 'Brand strategist'])}",
        f"🎯 {random.choice(['Marketing', 'Business', 'Fitness', 'Travel', 'Food'])} | 📧 {username}@gmail.com",
    ]

    posts = []
    num_posts = min(20, random.randint(8, 25))
    base_engagement = followers * random.uniform(0.01, 0.05)

    for i in range(num_posts):
        days_ago = i * random.uniform(1, 4)
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        likes = int(base_engagement * random.uniform(0.5, 2.5))
        comments = int(likes * random.uniform(0.02, 0.15))

        post_type = random.choices(
            ["image", "video", "carousel"],
            weights=[40, 35, 25]
        )[0]

        hashtags_list = [
            "#contentcreator", "#socialmedia", "#marketing", "#branding",
            "#growth", "#digitalmarketing", "#reels", "#instagram",
            "#business", "#entrepreneur", "#success", "#motivation",
            "#lifestyle", "#creative", "#photography", "#design",
            "#strategy", "#inspiration", "#trending", "#viral",
        ]
        num_tags = random.randint(5, 20)
        post_tags = random.sample(hashtags_list, min(num_tags, len(hashtags_list)))

        posts.append({
            "shortcode": f"demo{i}",
            "caption": f"Amazing content about {random.choice(['growth', 'strategy', 'design', 'lifestyle', 'business', 'creativity'])}! {' '.join(post_tags[:3])}",
            "likes": likes,
            "comments": comments,
            "date": f"{date} {random.randint(9,21):02d}:{random.randint(0,59):02d}",
            "is_video": post_type == "video",
            "is_carousel": post_type == "carousel",
            "media_type": post_type,
            "url": f"https://instagram.com/p/demo{i}",
            "thumbnail_url": "",
            "hashtags": post_tags,
            "mentions": [],
        })

    # Build profile data structure that analyzer expects
    class DemoProfile:
        pass

    profile = DemoProfile()
    profile.username = username
    full_names = ["", "Creative Studio", "Official", "HQ", "Co."]
    profile.full_name = f"{username.title()} {random.choice(full_names)}".strip()
    profile.bio = random.choice(bios)
    profile.followers = followers
    profile.following = following
    profile.post_count = post_count
    profile.is_verified = is_verified
    profile.is_business = is_business
    profile.is_private = False
    profile.profile_pic_url = f"https://i.pravatar.cc/150?u={username}"
    profile.external_url = f"https://{username}.com"

    # Convert posts to PostData-like objects
    from lib.scraper import PostData
    profile.posts = [
        PostData(
            shortcode=p["shortcode"],
            caption=p["caption"],
            likes=p["likes"],
            comments=p["comments"],
            date=p["date"],
            is_video=p["is_video"],
            is_carousel=p["is_carousel"],
            media_type=p["media_type"],
            url=p["url"],
            thumbnail_url=p["thumbnail_url"],
            hashtags=p["hashtags"],
            mentions=p["mentions"],
        )
        for p in posts
    ]

    analyzer = ContentAnalyzer(profile)
    result = analyzer.full_analysis()
    result["_demo"] = True
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    username = data.get("username", "").strip().replace("@", "").lower()
    max_posts = min(int(data.get("max_posts", 30)), 50)

    if not username:
        return jsonify({"error": "Username is required"}), 400

    # Check cache first
    cache_key = f"{username}_{max_posts}"
    if cache_key in analysis_cache:
        return jsonify(analysis_cache[cache_key])

    # Try real scrape first
    try:
        scraper = InstagramScraper()
        profile = scraper.fetch_profile(username, max_posts=max_posts)

        if profile is None:
            return jsonify({"error": f"Profile '@{username}' not found."}), 404

        if profile.is_private:
            return jsonify({"error": f"Profile '@{username}' is private."}), 403

        analyzer = ContentAnalyzer(profile)
        result = analyzer.full_analysis()
        analysis_cache[cache_key] = result
        return jsonify(result)

    except Exception as e:
        error_msg = str(e)

        # If Instagram blocks, fall back to demo mode with a warning
        if "INSTAGRAM_BLOCKED" in error_msg or "blocking" in error_msg.lower() or "403" in error_msg:
            # Generate demo data so the UI still works
            demo_result = generate_demo_data(username)
            demo_result["_warning"] = (
                "⚠️ Instagram is blocking server requests. Showing DEMO DATA. "
                "To get real data, set IG_SESSIONID, IG_CSRFTOKEN, IG_DS_USER_ID "
                "environment variables in Railway, then redeploy."
            )
            demo_result["_error_details"] = error_msg[:500]
            analysis_cache[cache_key] = demo_result
            return jsonify(demo_result)

        return jsonify({"error": error_msg}), 500


@app.route("/api/cached/<username>")
def cached_analysis(username):
    for key, val in analysis_cache.items():
        if key.startswith(username.lower() + "_"):
            return jsonify(val)
    return jsonify({"error": "No cached analysis found"}), 404


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        filename
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
