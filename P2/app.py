#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import datetime
import os
from logging.config import dictConfig

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool
from sqlalchemy.exc import SQLAlchemyError  # Make sure this import is added at the top of your file
# pip install sqlalchemy

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
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://bank:bank@postgres/bank") # change!!

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


def is_integer(s):
    """Returns True if string is an integer number."""
    try:
        int(s)
        return True
    except ValueError:
        return False


@app.route("/", methods=("GET",))
@app.route("/player", methods=("GET",))
@limiter.limit("1 per second")
def players_index():
    """Show the list of players sorted by most recent player attributes date first."""
    
    with pool.connection() as conn:
        with conn.cursor() as cur:
            # Querying the SQL View to get player information
            players = cur.execute(
                """
                SELECT player_fifa_api_id, player_name, date
                FROM player_attributes_view
                ORDER BY date DESC
                LIMIT 20;
                """,
                {}
            ).fetchall()
            log.debug(f"Found {cur.rowcount} players.")

    return render_template("player/index.html", players=players)

@app.route("/player/<player_api_id>/update", methods=("GET",))
#@app.route("/player/<int:player_api_id>/update", methods=["GET"])
@limiter.limit("1 per second")
def player_update_view(player_api_id):
    """Show the editable form for updating player details."""

    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                player = cur.execute(
                    """
                    SELECT player_api_id, player_name
                    FROM player_attributes_view
                    WHERE player_api_id = %(player_api_id)s;
                    """,
                    {"player_api_id": player_api_id},
                ).fetchone()
                #  SELECT player_name, preferred_foot, crossing, potential
                #        FROM player_attributes
                #        WHERE player_fifa_api_id = %s
                #        ORDER BY date DESC LIMIT 1;
                log.debug(f"Found {cur.rowcount} rows.")
        if not player:
                raise ValueError("Player not found.")

        # At the end of the `connection()` context, the transaction is committed
        # or rolled back, and the connection returned to the pool.

        #return render_template("player/update.html", player=player)
        return render_template("player/update.html", player=player,  player_api_id=player_api_id)

    except Exception as e:
        # Handle errors (e.g., player not found, database issue)
        error_message = str(e)
        return render_template("player/update.html", error_message=error_message)


@app.route("/accounts/<account_number>/update", methods=("POST",))


def player_update_save(player_api_id):
    """Save the updated player details and redirect to players index."""

    '''def insert_player_attributes(data):
        # Assuming you have access to db and player_attributes model
        try:
            new_attribute = PlayerAttributes(**data)  # Assuming PlayerAttributes is the model for your player_attributes table
            db.session.add(new_attribute)
            db.session.commit()
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            raise e'''
        
    '''player_api_id = request.form["player_api_id"]

    error = None

    if not player_api_id:
        error = "player_api_id is required."
    if not is_integer(player_api_id):
        error = "player_api_id is required to be integer."

    if error is not None:
        flash(error)
    else:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE player_attributes
                    SET balance = %(balance)s
                    WHERE player_api_id = %(player_api_id)s;
                    """,
                    {"player_api_id": player_api_id, "balance": balance},
                )
                # The result of this statement is persisted immediately by the database
                # because the connection is in autocommit mode.

        # The connection is returned to the pool at the end of the `connection()` context but,
        # because it is not in a transaction state, no COMMIT is executed.

        return redirect(url_for("players_index_view"))'''

    try:
         # Extract the data from the form
        data = {
            "player_api_id": player_api_id,
            "gk_reflexes": request.form['gk_reflexes'],
            "gk_handling": request.form['gk_handling'],
            "gk_kicking": request.form['gk_kicking'],
            "gk_positioning": request.form['gk_positioning'],
            "overall_rating": request.form['overall_rating'],
            "potential": request.form['potential'],
            "crossing": request.form['crossing'],
            "finishing": request.form['finishing'],
            "heading_accuracy": request.form['heading_accuracy'],
            "short_passing": request.form['short_passing'],
            "volleys": request.form['volleys'],
            "dribbling": request.form['dribbling'],
            "curve": request.form['curve'],
            "free_kick_accuracy": request.form['free_kick_accuracy'],
            "long_passing": request.form['long_passing'],
            "ball_control": request.form['ball_control'],
            "acceleration": request.form['acceleration'],
            "sprint_speed": request.form['sprint_speed'],
            "agility": request.form['agility'],
            "reactions": request.form['reactions'],
            "balance": request.form['balance'],
            "shot_power": request.form['shot_power'],
            "jumping": request.form['jumping'],
            "stamina": request.form['stamina'],
            "strength": request.form['strength'],
            "long_shots": request.form['long_shots'],
            "aggression": request.form['aggression'],
            "interceptions": request.form['interceptions'],
            "positioning": request.form['positioning'],
            "vision": request.form['vision'],
            "penalties": request.form['penalties'],
            "marking": request.form['marking'],
            "standing_tackle": request.form['standing_tackle'],
            "sliding_tackle": request.form['sliding_tackle'],
            "gk_diving": request.form['gk_diving'],
            "attacking_work_rate": request.form['attacking_work_rate'],
            "defensive_work_rate": request.form['defensive_work_rate'],
            "preferred_foot": request.form['preferred_foot'],
            "date": datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M'),  # Add the datetime object to the data dictionary
        }

        # strftime('%Y-%m-%d %H:%M:%S')
        date_value = datetime.strptime(request.form['date'], '%Y-%m-%d %H:%M:%S')

        
        # You can use datetime if required datetime.datetime.now(), 
        # player_name = request.form["player_name"]

        # Validate the input data (basic checks)
        '''if not player_name or not preferred_foot or not crossing or not potential:
            raise ValueError("All fields are required.")'''

        # Update the player_attributes table with the new date            
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Update the player attributes
                set_clause = ", ".join([f"{key} = %s" for key in data.keys() if key != "player_api_id"])
                sql_query = f"""
                    UPDATE player_attributes
                    SET {set_clause}
                    WHERE player_api_id = %s
                """
                # Adiciona o player_api_id no final para a cláusula WHERE
                #   SET new_attribute = %s
                values = list(data.values()) + [player_api_id]
                
                # Executar o comando
                cur.execute(sql_query, values)
                conn.commit()

        # Redirect to players index after success
        # Success: Redirect to players_index
        flash("Player attributes updated successfully!", "success")
        return redirect(url_for("players_index_view"))

    except ValueError as e:  # User-related error
        error_message = str(e)
        return render_template(
            "player/update.html",
            player_api_id=player_api_id,
            error_message=error_message,
        )
    
    except SQLAlchemyError as e:
        # Handle database errors, e.g., connection issues, constraint violations
        flash(f"Error updating player: {str(e)}", "error")
        return redirect(url_for('player_update_view', player_api_id=player_api_id))
    
    except Exception as e:
        # Handle errors (e.g., invalid data, database issues)
        # Use this approach for server-related errors (e.g., database issues, backend validation) or severe failures where it's not safe to stay on the current page.
        
        # !! added later
        app.logger.error(f"Unexpected error updating player: {str(e)}")

        flash(f"Unexpected error occurred. Please try again later: {e}", 'error')
        return redirect(url_for("player_update_view", player_api_id=player_api_id))


'''@app.route("/accounts/<account_number>/delete", methods=("POST",))
def account_delete(account_number):
    """Delete the account."""

    with pool.connection() as conn:
        with conn.cursor() as cur:
            with conn.transaction():
                # BEGIN is executed, a transaction started
                cur.execute(
                    """
                    DELETE FROM depositor
                    WHERE account_number = %(account_number)s;
                    """,
                    {"account_number": account_number},
                )
                cur.execute(
                    """
                    DELETE FROM account
                    WHERE account_number = %(account_number)s;
                    """,
                    {"account_number": account_number},
                )
                # These two operations run atomically in the same transaction

        # COMMIT is executed at the end of the block.
        # The connection is in idle state again.

    # The connection is returned to the pool at the end of the `connection()` context

    return redirect(url_for("account_index"))

'''
@app.route("/ping", methods=("GET",))
@limiter.exempt
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
    app.run()
