import os

from flask import Flask, request, jsonify

from database import (
    initialize_database,
    get_or_create_user,
    get_user,
    get_balance
)


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

initialize_database()


# ============================================================
# CONVERT SQLITE ROW TO DICTIONARY
# ============================================================

def row_to_dict(row):

    if row is None:
        return None

    return {
        "id": row["id"],
        "telegram_id": row["telegram_id"],
        "username": row["username"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "balance": row["balance"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "message": "Game Zone backend is running."
    })


# ============================================================
# CREATE OR GET USER
# ============================================================

@app.route("/api/user", methods=["POST"])
def create_or_get_user():

    data = request.get_json(silent=True) or {}

    telegram_id = data.get("telegram_id")

    if not telegram_id:

        return jsonify({
            "success": False,
            "error": "telegram_id is required"
        }), 400

    try:

        telegram_id = int(telegram_id)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "error": "telegram_id must be a number"
        }), 400

    username = data.get("username", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    user = get_or_create_user(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )

    return jsonify({
        "success": True,
        "user": row_to_dict(user)
    })


# ============================================================
# GET BALANCE
# ============================================================

@app.route("/api/balance/<int:telegram_id>", methods=["GET"])
def balance(telegram_id):

    user = get_user(telegram_id)

    if not user:

        return jsonify({
            "success": False,
            "error": "User not found"
        }), 404

    return jsonify({
        "success": True,
        "telegram_id": telegram_id,
        "balance": get_balance(telegram_id)
    })


# ============================================================
# TEST USER
# ============================================================

@app.route("/api/test-user/<int:telegram_id>", methods=["GET"])
def test_user(telegram_id):

    user = get_or_create_user(
        telegram_id=telegram_id,
        username="demo_user",
        first_name="Demo",
        last_name="User"
    )

    return jsonify({
        "success": True,
        "user": row_to_dict(user)
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )