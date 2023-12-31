from flask import Flask, render_template, request, jsonify, make_response, Response
import requests
import json
import re
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
    bookings = json.load(jsf)["bookings"]


@app.route("/", methods=['GET'])
def home():
    return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"


@app.route("/bookings", methods=['GET'])
def get_bookings():
    """
    Retrieve the list of bookings.

    :return: A response object containing the list of bookings in JSON format.
    """
    return make_response(jsonify(bookings), 200)


@app.route("/bookings/<user_id>", methods=['GET'])
def get_bookings_byuser(user_id: str) -> Response:
    """
    Get bookings for a specific user
    :param user_id: a specific user id

   :return: Response that contains the bookings for a specific user
   """
    # Verification si l'id est dans la base de donnees
    for booking in bookings:
        if booking["userid"] == user_id:
            return make_response(jsonify(booking), 200)

    return make_response(jsonify({"error": "User not found"}), 404)


@app.route("/bookings/<user_id>", methods=['POST'])
def add_booking(user_id: str) -> Response:
    """
     Add a booking for a specific user

    :param str user_id: a specific user id
    :return: Response that contains the bookings for a specific user
    """
    # Récupération des données de l'utilisateur sinon une liste vide
    user_bookings = {}

    for booking in bookings:
        if booking["userid"] == user_id:
            user_bookings = booking["dates"]
            break

    # Récupération des données de la requête
    data = request.get_json()
    if data is None:
        return make_response(jsonify({"error": "Bad request"}), 400)

    # Vérification de la validité des données
    errors = []

    if "date" not in data:
        errors.append({"date": "Missing field"})
    elif not re.match(r'^(\d{4})(0[1-9]|1[0-2])(0[1-9]|[1-2]\d|3[0-1])$', data["date"]):
        errors.append({"date": "Invalid date format, expected YYYYMMDD"})
    else:
        # Vérification de la date de réservation du film est bien programmée
        response_showtimes = requests.get(f'http://showtime:3202/showtimes/{data["date"]}')
        if response_showtimes.status_code == 404:
            errors.append({"date": "Date not found"})
        else:
            showtime = response_showtimes.json()
            if "movie" in data and data["movie"] not in showtime["movies"]:
                errors.append({"movie": "Movie not scheduled for this date"})
                

    if "movie" not in data:
        errors.append({"movie": "Missing field"})

    if errors:
        return make_response(jsonify({"errors": errors}), 400)

    for booking in user_bookings:
        if booking["date"] == data["date"]:

            if data["movie"] in booking["movies"]:
                return make_response(jsonify({"error": "Movie already booked for this date"}), 400)

            booking["movies"].append(data["movie"])
            break
    else:
        user_bookings.append({"date": data["date"], "movies": [data["movie"]]})

    for booking in bookings:
        if booking["userid"] == user_id:
            booking["dates"] = user_bookings
            break

    return make_response(jsonify({"message": "Booking added", "user_bookings": user_bookings}), 200)


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
