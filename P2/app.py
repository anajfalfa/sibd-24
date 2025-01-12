#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import os
from decimal import Decimal, InvalidOperation
from logging.config import dictConfig
from datetime import datetime

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

app = Flask(__name__)
app.config.from_prefixed_env()
log = app.logger
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=RATELIMIT_STORAGE_URI,
)

# Use the DATABASE_URL environment variable if it exists, otherwise use the default.
# Use the format postgres://username:password@hostname/database_name to connect to the database.
DATABASE_URL = "postgres://db:db@postgres/db"

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    kwargs={
        "autocommit": True,  # If True don’t start transactions automatically.
        "row_factory": namedtuple_row,
    },
    min_size=4,
    max_size=10,
    open=True,
    # check=ConnectionPool.check_connection,
    name="postgres_pool",
    timeout=5,
)


def is_decimal(s):
    """Returns True if string is a parseable Decimal number."""
    try:
        Decimal(s)
        return True
    except InvalidOperation:
        return False


@app.route("/", methods=("GET",))
@app.route("/players", methods=("GET",))
@limiter.limit("1 per second")
def players_index():
    """Show all the accounts, most recent first."""

    with pool.connection() as conn:
        with conn.cursor() as cur:
            players = cur.execute(
                """
                SELECT player_id, player_name, date
                FROM players_index_view
                ORDER BY date DESC
                LIMIT 20;
                
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")
    return render_template("player/index.html", players=players)


@app.route("/players/<player_api_id>/update", methods=("GET",))
@limiter.limit("1 per second")
def player_update_view(player_api_id):
    """Show the page to update the account balance."""

    with pool.connection() as conn:
        with conn.cursor() as cur:
            player = cur.execute(
                """
                SELECT pa.*,  piv.player_name
                FROM player_attributes pa
                JOIN players_index_view piv
                ON pa.player_api_id = piv.player_id AND pa.date = piv.date
                WHERE player_api_id = %(player_api_id)s;
                """,
                {"player_api_id": player_api_id},
            ).fetchone()
            log.debug(f"Found {cur.rowcount} rows.")
    if not player:
        raise ValueError("Player not found.")

    # At the end of the `connection()` context, the transaction is committed
    # or rolled back, and the connection returned to the pool.
    return render_template("player/update.html", player=player)


@app.route("/players/<player_api_id>/update", methods=("POST",))
def player_update_save(player_api_id):
    """Update the account balance."""

    try:
        # Extract the data from the form and only include fields that are not empty
        data = {}
        # List of fields to update
        fields = [
            "gk_reflexes", "gk_handling", "gk_kicking", "gk_positioning",
            "overall_rating", "potential", "crossing", "finishing",
            "heading_accuracy", "short_passing", "volleys", "dribbling",
            "curve", "free_kick_accuracy", "long_passing", "ball_control",
            "acceleration", "sprint_speed", "agility", "reactions",
            "balance", "shot_power", "jumping", "stamina", "strength",
            "long_shots", "aggression", "interceptions", "positioning",
            "vision", "penalties", "marking", "standing_tackle", "sliding_tackle",
            "gk_diving", "attacking_work_rate", "defensive_work_rate",
            "preferred_foot", "date"
        ]

        for field in fields:
            value = request.form.get(field, None)
            if value is not None and value != "":
                data[field] = value
        
        data["player_api_id"] = player_api_id

        if not data:
            flash("No changes detected.", "info")
            return redirect(url_for("player_update", player_api_id=player_api_id))

        if "date" in data:
            try:
                converted_date = datetime.strptime(data["date"], '%Y-%m-%dT%H:%M')  #datetime type
                data["date"] = converted_date
            except ValueError:
                raise ValueError("Invalid date format. Please use 'YYYY-MM-DDTHH:MM'.")

        ranged_fields = ("gk_reflexes", "gk_handling", "gk_kicking", "gk_positioning",
            "overall_rating", "potential", "crossing", "finishing",
            "heading_accuracy", "short_passing", "volleys", "dribbling",
            "curve", "free_kick_accuracy", "long_passing", "ball_control",
            "acceleration", "sprint_speed", "agility", "reactions",
            "balance", "shot_power", "jumping", "stamina", "strength",
            "long_shots", "aggression", "interceptions", "positioning",
            "vision", "penalties", "marking", "standing_tackle", "sliding_tackle",
            "gk_diving" )
        
        for field in ranged_fields:
            if field in data:
                try:
                    value = int(data[field])
                    if not (0 <= value <= 100):
                        raise ValueError(f"Invalid value for {field}. Must be between 0 and 100.")
                except ValueError:
                    raise ValueError(f"{field} must be a valid integer between 0 and 100.")

        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT player_name FROM players_index_view WHERE player_id = %s", (player_api_id,))
                player_name = cur.fetchone()
                
                if player_name:
                    player_name = player_name[0]
                else:
                    raise ValueError("Player not found.")
                
        with pool.connection() as conn:
            with conn.cursor() as cur:
                set_clause = ", ".join([f"{key} = %s" for key in data.keys() if key != "player_api_id" ])
                log.debug(set_clause)    
                sql_query = f"""
                    UPDATE player_attributes
                    SET {set_clause}
                    WHERE player_api_id = %s
                """
                values = list(data.values())

                cur.execute(sql_query, values) 
                conn.commit()
                # The result of this statement is persisted immediately by the database
                # because the connection is in autocommit mode.

    # The connection is returned to the pool at the end of the `connection()` context but,
    # because it is not in a transaction state, no COMMIT is executed.
   

        flash(f"Player {player_name}'s attributes updated successfully!", "success")
        return redirect(url_for("players_index"))
        
    except ValueError as e:  # User-related error
        error_message = str(e)
        return render_template(
            "player/update.html",
            player_api_id=player_api_id,
            error_message=error_message,
        )
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return render_template("player/update.html", message="An unexpected error occurred.")



@app.route("/ping", methods=("GET",))
@limiter.exempt
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
    app.run()
