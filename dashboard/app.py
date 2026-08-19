from __future__ import annotations
from flask import Flask, render_template
from config import load_settings
from database import Database

app = Flask(__name__)

settings = load_settings()

database = Database(
    settings.database_path
)

@app.route("/")
def index():
    listings = (
        database.get_dashboard_listings()
    )

    return render_template(
        "index.html",
        listings=listings,
    )

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )