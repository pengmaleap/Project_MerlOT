import json
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
DATA_PATH = os.path.join(os.path.dirname(__file__), "featured_movies.json")
with open(DATA_PATH, "r", encoding="utf-8") as data_file:
    featured_movies = json.load(data_file)

MOOD_KEYWORDS = {
    "dark": ["Horror", "Crime", "Drama"],
    "mysterious": ["Horror", "Crime", "Sci-Fi"],
    "funny": ["Comedy"],
    "romantic": ["Romance", "Drama"],
    "action": ["Action"],
    "epic": ["Adventure", "Drama"],
    "hero": ["Action", "Adventure"],
    "scifi": ["Sci-Fi"],
    "sci-fi": ["Sci-Fi"],
}


def normalize(s):
    return (s or "").strip().lower()


def parse_first_year(year_text):
    digits = "".join(ch for ch in year_text if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    return None


def era_match(year_text, era):
    year = parse_first_year(year_text)
    if year is None or era == "anytime":
        return True
    if era == "new":
        return year >= 2020
    if era == "modern":
        return 2000 <= year <= 2019
    if era == "old":
        return year < 2000
    return True


def extract_mood_genres(mood_text):
    mood = normalize(mood_text)
    matched = set()
    for key, genres in MOOD_KEYWORDS.items():
        if key in mood:
            matched.update(genres)
    return matched


def score_movie(movie, prefs):
    score = 0
    reasons = []

    pref_genres = set(prefs.get("genres", []))
    movie_genres = {normalize(g) for g in movie.get("genres", [])}
    if pref_genres:
        overlap = pref_genres.intersection(movie_genres)
        if overlap:
            score += 3 * len(overlap)
            reasons.append(f"genre match: {', '.join(sorted(overlap))}")

    pref_type = normalize(prefs.get("type"))
    if pref_type in ("movies", "movie"):
        pref_type = "movie"
    elif pref_type in ("tv", "tv series", "series"):
        pref_type = "tv"
    if pref_type and pref_type != "both":
        movie_type = normalize(movie.get("type"))
        if pref_type in movie_type:
            score += 2
            reasons.append("format match")
        else:
            score -= 2
            reasons.append("format mismatch")

    mood_genres = extract_mood_genres(prefs.get("mood"))
    if mood_genres:
        overlap = mood_genres.intersection(movie_genres)
        if overlap:
            score += 2 * len(overlap)
            reasons.append(f"mood match: {', '.join(sorted(overlap))}")

    era = normalize(prefs.get("era"))
    if era and era != "anytime":
        if era_match(movie.get("year", ""), era):
            score += 1
            reasons.append("era match")
        else:
            score -= 1
            reasons.append("era mismatch")

    return score, reasons


def has_required_genre(movie, prefs):
    pref_genres = set(prefs.get("genres", []))
    if not pref_genres:
        return True
    movie_genres = {normalize(g) for g in movie.get("genres", [])}
    return bool(pref_genres.intersection(movie_genres))
CORS(app)  # 🔥 allow React to call Flask

@app.route("/api/hello")
def hello():
    return jsonify({"message": "Hello from Flask"})

@app.route("/api/featured-movies")
def get_featured_movies():
    return jsonify(featured_movies)

@app.route("/api/recommendations")
def get_recommendations():
    # Example query params:
    # ?genres=Action,Drama&type=movies&era=new&mood=dark and mysterious
    raw_genres = normalize(request.args.get("genres", ""))
    genres = [normalize(g) for g in raw_genres.split(",") if g.strip()]
    prefs = {
        "genres": genres,
        "type": normalize(request.args.get("type")),
        "era": normalize(request.args.get("era")),
        "mood": request.args.get("mood", ""),
    }

    scored = []
    for movie in featured_movies:
        if not has_required_genre(movie, prefs):
            continue
        score, reasons = score_movie(movie, prefs)
        scored.append(
            {
                "score": score,
                "reasons": reasons,
                "movie": movie,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(scored)

if __name__ == "__main__":
    app.run(debug=True)
