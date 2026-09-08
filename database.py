import sqlite3
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "gamezone.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------
    # USERS
    # --------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER NOT NULL DEFAULT 10000,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------
    # TRANSACTIONS
    # --------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------
    # GAME HISTORY
    # --------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            game TEXT NOT NULL,
            bet_amount INTEGER NOT NULL,
            result TEXT,
            win_amount INTEGER NOT NULL DEFAULT 0,
            balance_after INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------
    # MINES ACTIVE GAMES
    # --------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mines_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            telegram_id INTEGER NOT NULL,

            bet_amount INTEGER NOT NULL,

            grid_size INTEGER NOT NULL DEFAULT 25,

            mine_count INTEGER NOT NULL,

            mines_json TEXT NOT NULL,

            revealed_json TEXT NOT NULL DEFAULT '[]',

            multiplier REAL NOT NULL DEFAULT 1.0,

            potential_win INTEGER NOT NULL DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'active',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


# ======================================================
# USER FUNCTIONS
# ======================================================

def get_or_create_user(
    telegram_id,
    username=None,
    first_name=None,
    last_name=None
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    user = cursor.fetchone()

    if user:
        cursor.execute("""
            UPDATE users
            SET
                username = ?,
                first_name = ?,
                last_name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (
            username,
            first_name,
            last_name,
            telegram_id
        ))

        connection.commit()

    else:
        cursor.execute("""
            INSERT INTO users (
                telegram_id,
                username,
                first_name,
                last_name,
                balance
            )
            VALUES (?, ?, ?, ?, 10000)
        """, (
            telegram_id,
            username,
            first_name,
            last_name
        ))

        connection.commit()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    user = cursor.fetchone()

    connection.close()

    return user


def get_user(telegram_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    user = cursor.fetchone()

    connection.close()

    return user


def get_balance(telegram_id):
    user = get_user(telegram_id)

    if not user:
        return None

    return user["balance"]


# ======================================================
# BALANCE FUNCTIONS
# ======================================================

def change_balance(
    telegram_id,
    amount,
    transaction_type,
    description=""
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT balance
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    user = cursor.fetchone()

    if not user:
        connection.close()
        return None

    current_balance = user["balance"]

    new_balance = current_balance + amount

    if new_balance < 0:
        connection.close()
        return None

    cursor.execute("""
        UPDATE users
        SET
            balance = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
    """, (
        new_balance,
        telegram_id
    ))

    cursor.execute("""
        INSERT INTO transactions (
            telegram_id,
            type,
            amount,
            balance_after,
            description
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        telegram_id,
        transaction_type,
        amount,
        new_balance,
        description
    ))

    connection.commit()
    connection.close()

    return new_balance


# ======================================================
# MINES FUNCTIONS
# ======================================================

def create_mines_game(
    telegram_id,
    bet_amount,
    mine_count,
    mines
):
    """
    Creates one active Mines game.

    mines must be a Python list.

    Example:
        [2, 7, 11]
    """

    connection = get_connection()
    cursor = connection.cursor()

    # Cancel any older active game for this user.
    cursor.execute("""
        UPDATE mines_games
        SET
            status = 'cancelled',
            updated_at = CURRENT_TIMESTAMP
        WHERE
            telegram_id = ?
            AND status = 'active'
    """, (telegram_id,))

    cursor.execute("""
        INSERT INTO mines_games (
            telegram_id,
            bet_amount,
            grid_size,
            mine_count,
            mines_json,
            revealed_json,
            multiplier,
            potential_win,
            status
        )
        VALUES (?, ?, 25, ?, ?, '[]', 1.0, ?, 'active')
    """, (
        telegram_id,
        bet_amount,
        mine_count,
        json.dumps(mines),
        bet_amount
    ))

    game_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return game_id


def get_active_mines_game(telegram_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM mines_games
        WHERE
            telegram_id = ?
            AND status = 'active'
        ORDER BY id DESC
        LIMIT 1
    """, (telegram_id,))

    game = cursor.fetchone()

    connection.close()

    return game


def get_mines_game(game_id, telegram_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM mines_games
        WHERE
            id = ?
            AND telegram_id = ?
        LIMIT 1
    """, (
        game_id,
        telegram_id
    ))

    game = cursor.fetchone()

    connection.close()

    return game


def update_mines_game(
    game_id,
    telegram_id,
    revealed_tiles,
    multiplier,
    potential_win
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE mines_games
        SET
            revealed_json = ?,
            multiplier = ?,
            potential_win = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE
            id = ?
            AND telegram_id = ?
            AND status = 'active'
    """, (
        json.dumps(revealed_tiles),
        multiplier,
        potential_win,
        game_id,
        telegram_id
    ))

    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return updated


def finish_mines_game(
    game_id,
    telegram_id,
    status
):
    """
    status should normally be:
        won
        lost
        cashed_out
        cancelled
    """

    allowed_statuses = {
        "won",
        "lost",
        "cashed_out",
        "cancelled"
    }

    if status not in allowed_statuses:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE mines_games
        SET
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE
            id = ?
            AND telegram_id = ?
            AND status = 'active'
    """, (
        status,
        game_id,
        telegram_id
    ))

    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return updated


def delete_active_mines_game(telegram_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM mines_games
        WHERE
            telegram_id = ?
            AND status = 'active'
    """, (telegram_id,))

    connection.commit()
    connection.close()


# ======================================================
# TEST / INITIALIZATION
# ======================================================

if __name__ == "__main__":
    initialize_database()

    print()
    print("GameZone database initialized successfully.")
    print()
    print(f"Database: {DATABASE_FILE}")
    print()
    print("Tables:")
    print("- users")
    print("- transactions")
    print("- game_history")
    print("- mines_games")
