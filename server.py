import os
import hmac
import hashlib
import time
import json
import urllib.parse

from flask import Flask, request, jsonify
from flask_cors import CORS

from database import (
    initialize_database,
    get_or_create_user,
    get_user,
    get_balance
)

app = Flask(__name__)

# Allow the Telegram Mini App to communicate with the backend.
CORS(app)

# Initialize database.
initialize_database()


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


def validate_telegram_init_data(init_data):
    """
    Verify Telegram Mini App initData.

    Returns the verified Telegram user dictionary
    when the data is valid.
    Returns None when invalid.
    """

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not configured.")
        return None

    if not init_data:
        print("ERROR: initData was not provided.")
        return None

    try:
        parsed = urllib.parse.parse_qs(
            init_data,
            keep_blank_values=True
        )

        received_hash = parsed.get("hash", [None])[0]

        if not received_hash:
            print("ERROR: Telegram hash missing.")
            return None

        data_pairs = []

        for key in sorted(parsed.keys()):

            if key == "hash":
                continue

            value = parsed[key][0]

            data_pairs.append(
                f"{key}={value}"
            )

        data_check_string = "\n".join(data_pairs)

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode("utf-8"),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            print("ERROR: Telegram authentication hash invalid.")
            return None

        auth_date = parsed.get(
            "auth_date",
            [None]
        )[0]

        if auth_date:

            try:

                auth_timestamp = int(auth_date)

                # Allow authentication data to be used
                # for up to 24 hours.
                if time.time() - auth_timestamp > 86400:
                    print("ERROR: Telegram authentication expired.")
                    return None

            except ValueError:

                print("ERROR: Invalid auth_date.")
                return None

        user_json = parsed.get(
            "user",
            [None]
        )[0]

        if not user_json:
            print("ERROR: Telegram user data missing.")
            return None

        user_data = json.loads(user_json)

        return user_data

    except Exception as error:

        print(
            "Telegram authentication error:",
            error
        )

        return None


@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "message": "Game Zone backend is running."
    })


@app.route("/api/user", methods=["POST"])
def create_or_get_user():

    data = request.get_json(
        silent=True
    ) or {}

    init_data = data.get("initData")

    # Verify that the request actually came
    # from Telegram.
    telegram_user = validate_telegram_init_data(
        init_data
    )

    if not telegram_user:

        return jsonify({
            "success": False,
            "error": "Invalid Telegram authentication data"
        }), 401

    telegram_id = telegram_user.get("id")

    if not telegram_id:

        return jsonify({
            "success": False,
            "error": "Telegram user ID not found"
        }), 400

    username = telegram_user.get(
        "username",
        ""
    )

    first_name = telegram_user.get(
        "first_name",
        ""
    )

    last_name = telegram_user.get(
        "last_name",
        ""
    )

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


@app.route(
    "/api/balance/<int:telegram_id>",
    methods=["GET"]
)
def balance(telegram_id):

    user = get_user(
        telegram_id
    )

    if not user:

        return jsonify({
            "success": False,
            "error": "User not found"
        }), 404

    return jsonify({
        "success": True,
        "telegram_id": telegram_id,
        "balance": get_balance(
            telegram_id
        )
    })


@app.route(
    "/api/test-user/<int:telegram_id>",
    methods=["GET"]
)
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


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )