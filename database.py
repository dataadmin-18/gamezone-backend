import sqlite3
from pathlib import Path

# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_FILE = BASE_DIR / "gamezone.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# CREATE TABLES
# ============================================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()


    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # TRANSACTIONS
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # GAME HISTORY
    # --------------------------------------------------------

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


    connection.commit()

    connection.close()


# ============================================================
# CREATE / GET USER
# ============================================================

def get_or_create_user(
    telegram_id,
    username=None,
    first_name=None,
    last_name=None
):

    connection = get_connection()

    cursor = connection.cursor()


    # Check existing user

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    user = cursor.fetchone()


    if user:

        # Update current Telegram information

        cursor.execute(
            """
            UPDATE users

            SET
                username = ?,
                first_name = ?,
                last_name = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE telegram_id = ?
            """,

            (
                username,
                first_name,
                last_name,
                telegram_id
            )
        )

        connection.commit()


    else:

        # Create new user

        cursor.execute(
            """
            INSERT INTO users (
                telegram_id,
                username,
                first_name,
                last_name,
                balance
            )

            VALUES (?, ?, ?, ?, 10000)
            """,

            (
                telegram_id,
                username,
                first_name,
                last_name
            )
        )

        connection.commit()


    # Get final user record

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    user = cursor.fetchone()

    connection.close()

    return user


# ============================================================
# GET USER
# ============================================================

def get_user(telegram_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    user = cursor.fetchone()

    connection.close()

    return user


# ============================================================
# GET BALANCE
# ============================================================

def get_balance(telegram_id):

    user = get_user(
        telegram_id
    )

    if not user:
        return None

    return user["balance"]


# ============================================================
# CHANGE BALANCE
# ============================================================

def change_balance(
    telegram_id,
    amount,
    transaction_type,
    description=""
):

    connection = get_connection()

    cursor = connection.cursor()


    # Get current balance

    cursor.execute(
        """
        SELECT balance
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    user = cursor.fetchone()


    if not user:

        connection.close()

        return None


    current_balance = user["balance"]

    new_balance = current_balance + amount


    # Prevent negative balance

    if new_balance < 0:

        connection.close()

        return None


    # Update balance

    cursor.execute(
        """
        UPDATE users

        SET
            balance = ?,
            updated_at = CURRENT_TIMESTAMP

        WHERE telegram_id = ?
        """,

        (
            new_balance,
            telegram_id
        )
    )


    # Record transaction

    cursor.execute(
        """
        INSERT INTO transactions (
            telegram_id,
            type,
            amount,
            balance_after,
            description
        )

        VALUES (?, ?, ?, ?, ?)
        """,

        (
            telegram_id,
            transaction_type,
            amount,
            new_balance,
            description
        )
    )


    connection.commit()

    connection.close()

    return new_balance


# ============================================================
# INITIALIZE DATABASE
# ============================================================


# ==========================================
# AVIATOR ACTIVE GAME SUPPORT
# ==========================================

def initialize_aviator_table():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aviator_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            bet_amount INTEGER NOT NULL,
            crash_multiplier REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            cashout_multiplier REAL,
            win_amount INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    connection.close()


def create_aviator_game(telegram_id, bet_amount, crash_multiplier):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE aviator_games
        SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
        WHERE telegram_id = ? AND status = 'active'
    """, (telegram_id,))
    cursor.execute("""
        INSERT INTO aviator_games (
            telegram_id, bet_amount, crash_multiplier, status
        ) VALUES (?, ?, ?, 'active')
    """, (telegram_id, bet_amount, crash_multiplier))
    game_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return game_id


def get_active_aviator_game(telegram_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM aviator_games
        WHERE telegram_id = ? AND status = 'active'
        ORDER BY id DESC LIMIT 1
    """, (telegram_id,))
    game = cursor.fetchone()
    connection.close()
    return game


def get_aviator_game(game_id, telegram_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM aviator_games
        WHERE id = ? AND telegram_id = ? LIMIT 1
    """, (game_id, telegram_id))
    game = cursor.fetchone()
    connection.close()
    return game


def finish_aviator_game(game_id, telegram_id, status, cashout_multiplier=0, win_amount=0):
    allowed = {"cashed_out", "lost", "cancelled"}
    if status not in allowed:
        return False
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE aviator_games
        SET status = ?, cashout_multiplier = ?, win_amount = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND telegram_id = ? AND status = 'active'
    """, (status, cashout_multiplier, win_amount, game_id, telegram_id))
    updated = cursor.rowcount > 0
    connection.commit()
    connection.close()
    return updated

if __name__ == "__main__":

    initialize_database()
    initialize_aviator_table()

    print()
    print("Game Zone database initialized.")
    print()
    print(
        f"Database: {DATABASE_FILE}"
    )