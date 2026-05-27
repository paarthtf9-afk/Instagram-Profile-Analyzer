"""
VISCOM Instagram Profile Analyzer
Flask application — serves the dashboard and API.
"""

import json
import os
import sys

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

    try:
        scraper = InstagramScraper()
        profile = scraper.fetch_profile(username, max_posts=max_posts)

        if profile is None:
            return jsonify({"error": f"Profile '@{username}' not found."}), 404

        if profile.is_private:
            return jsonify({"error": f"Profile '@{username}' is private. Only public profiles can be analyzed."}), 403

        analyzer = ContentAnalyzer(profile)
        result = analyzer.full_analysis()

        # Cache the result
        analysis_cache[cache_key] = result

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cached/<username>")
def cached_analysis(username):
    for key, val in analysis_cache.items():
        if key.startswith(username.lower() + "_"):
            return jsonify(val)
    return jsonify({"error": "No cached analysis found"}), 404


# Explicitly serve static files (helps with some hosting setups)
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        filename
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
