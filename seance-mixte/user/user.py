# Importation de datetime pour récupérer la date et l'heure actuelle
import datetime
import json
import uuid

import google.protobuf.json_format as json_format

import requests
from flask import Flask, request, jsonify, make_response, Response

import booking_pb2
import booking_pb2_grpc
import grpc

app = Flask(__name__)

PORT = 3004
HOST = '0.0.0.0'

with open('{}/data/users.json'.format("."), "r") as jsf:
    users = json.load(jsf)["users"]


##################### Utilities #####################
import datetime

def update_user_last_active(user_id: str) -> None:
    """
    Update the last active timestamp of a user.

    :param user_id: The ID of the user.

    :return: None
    """
    for user in users:
        if user["id"] == user_id:
            user["last_active"] = str(int(datetime.datetime.now().timestamp()))
            save_users()
            break

import json

def save_users() -> None:
    """
    Save the users to a JSON file.

    :return: None
    """
    with open('{}/data/users.json'.format("."), "w") as users_file:
        json.dump({"users": users}, users_file)


@app.route("/", methods=['GET'])
def home():
    return "<h1 style='color:blue'>Welcome to the User service!</h1>"


@app.route("/user/", methods=['POST'])
def add_user() -> Response:
    """
    Add a user to the database

    Notes
    -----
    This function adds a new user to the database based on the provided data in the request.
    The data should be in JSON format and should contain the following fields:
    - first_name: The first name of the user (required)
    - last_name: The last name of the user (required)

    If the data is not provided or is invalid, an error response will be returned.

    If the user already exists in the database, a conflict response will be returned.

    After successfully adding the user to the database, a success response will be returned
    with the user's information including the generated user ID.

    Parameters:
    ----------
    :return: Response object with a message and the id of the user
    """
    
    # Récupération des données de la requête
    data = request.get_json()
    if data is None:
        return make_response(jsonify({"error": "Bad request"}), 400)

    # Vérification de la validité des données
    errors = []

    # String vide ou non présent
    if "first_name" not in data or data["first_name"].strip() == "":
        errors.append({"first_name": "first name must not be empty"})

    if "last_name" not in data or data["last_name"].strip() == "":
        errors.append({"last_name": "last name must not be empty"})

    if errors:
        return make_response(jsonify({"errors": errors, "message": "Invalid data"}), 400)

    # id de l'utilisateur
    user_id = str(uuid.uuid4())

    # Verification si l'id est dans la base de donnees
    for user in users:
        if user["id"] == user_id:
            return make_response(jsonify({"error": "User already exists"}), 409)

    user = {
        "id": user_id,
        "name": data["first_name"] + " " + data["last_name"],
        "last_active": str(int(datetime.datetime.now().timestamp()))
    }

    users.append(user)

    save_users()

    return make_response(jsonify({"message": "User added", "data": user}), 201)


@app.route("/user/list", methods=['GET'])
def get_users() -> Response:
    """
    Get all the users

    Parameters:
    ----------
    :return: Response object with all the users
    """
    return make_response(jsonify(users), 200)


@app.route("/user/<user_id>", methods=['GET'])
def get_user(user_id: str) -> Response:
    """
    Get user information based on user_id.

    Parameters:
    ----------
    :param str user_id: The ID of the user.

    :return: The response containing the user information.
    """
    # Verification si l'id est dans la base de donnees
    for user in users:
        if user["id"] == user_id:
            return make_response(jsonify(user), 200)

    return make_response(jsonify({"error": "User not found"}), 404)


@app.route("/user/<user_id>", methods=['PUT'])
def update_user(user_id: str) -> Response:
    """
    Update user information based on user_id.

    Notes
    -----
    This function expects a JSON payload with 'first_name' and 'last_name' fields.

    If the user is found and the data is valid, the user's information is updated,
    and a success message is returned.

    If the user is not found, a 404 error is returned. If the request is malformed 
    or the data is invalid, a 400 error is returned with details about the issues.

    Parameters:
    ----------
    :param str user_id: The ID of the user.
    :return: The response containing the new user information.
    """
    # Récupération des données de la requête
    data = request.get_json()
    if data is None:
        return make_response(jsonify({"error": "Bad request"}), 400)

    # Vérification de la validité des données
    errors = []

    if "first_name" not in data:
        errors.append({"first_name": "first name must not be empty"})

    if "last_name" not in data:
        errors.append({"last_name": "last name must not be empty"})

    if errors:
        return make_response(jsonify({"errors": errors, "message": "Invalid data"}), 400)

    # Verification si l'id est dans la base de donnees
    for user in users:
        if user["id"] == user_id:
            user["name"] = data["first_name"] + " " + data["last_name"]
            user["last_active"] = str(int(datetime.datetime.now().timestamp()))
            return make_response(jsonify({"message": "User updated", "user": user}), 200)

    save_users()

    return make_response(jsonify({"error": "User not found"}), 404)


@app.route("/user/<user_id>", methods=['DELETE'])
def delete_user(user_id: str) -> Response:
    """
    Delete a user based on user_id.

    Notes
    -----
    If the user is found, it is deleted, and a success message is returned.

    If the user is not found, a 404 error is returned.

    Parameters:
    ----------
    :param str user_id: The ID of the user.

    :return: The response containing a success message.
    """
    # Verification si l'id est dans la base de donnees
    for user in users:
        if user["id"] == user_id:
            users.remove(user)

            save_users()

            return make_response(jsonify({"message": "User deleted"}), 200)

    return make_response(jsonify({"error": "User not found"}), 404)


##################### Graphql on Movie service #####################
@app.route("/<user_id>/movies", methods=['GET'])
def get_movies(user_id: str) -> Response:
    """
    Get all the movies

    Note:
    ----
    This function sends a GraphQL query to retrieve all movies from the movie service.
    
    If the request is successful (status code 200), the movies are returned in the response. 
    Otherwise, the response status code and error message from the movie service are returned.

    Parameters:
    ----------
    :param str user_id: The ID of the user.

    :return: Response object with all the movies
    """
    update_user_last_active(user_id)

    query = """
    {
      all_movies {
        id
        title
        director
        rating
      }   
    }
    """

    response = requests.post("http://movie:3001/graphql", json={"query": query})

    if response.status_code == 200:
        return make_response(jsonify(response.json()["data"]["all_movies"]), 200)

    return make_response(response.json(), response.status_code)

@app.route("/<user_id>/movies/<movie_id>", methods=['GET'])
def get_movie(user_id, movie_id) -> Response:
    """
    Retrieve details of a movie based on the provided movie ID

    Notes
    -----
    This function sends a GraphQL query to retrieve details of a specific movie from the movie service
    based on the provided movie ID.

    If the request is successful (status code 200), the movie details are returned in the response.

    If the movie is not found, a 404 error is returned with an appropriate error message.

    If there is an issue with the request, the response status code and error message from the movie service
    are returned.

    Parameters:
    ----------
    :param user_id: id of the user
    :param movie_id: id of the movie

    :return: Response object with the movie
    """
    update_user_last_active(user_id)

    query = """
    {
      movie_with_id(_id: "%s") {
        id
        title
        director
        rating
      }   
    }
    """ % movie_id

    response = requests.post("http://movie:3001/graphql", json={"query": query})

    if response.status_code == 200:
        response = response.json()["data"]["movie_with_id"]

        if response:
            return make_response(jsonify(response), 200)

        return make_response(jsonify({"error": "Movie not found"}), 404)

    return make_response(response.json(), response.status_code)

@app.route("/<user_id>/movies/<movie_id>/rating/<rating>", methods=['PUT'])
def update_movie_rating(user_id: str, movie_id: str, rating: str) -> Response:
    """
    Update the rating of a movie and update the user's last active timestamp.

    Notes
    -----
    This function sends a GraphQL mutation to update the rating of a specific movie from the movie service
    based on the provided movie ID.

    The new rating must be a number between 0 and 10; otherwise, a 400 error is returned with an appropriate
    error message.

    If the request is successful (status code 200), the updated movie details are returned
    in the response.

    If the movie is not found, a 404 error is returned with an appropriate error message.

    If there is an issue with the request, the response status code and error message from the movie service
    are returned.

    Parameters:
    ----------
    :param user_id: id of the user
    :param movie_id: id of the movie
    :param rating: new rating

    :return: Response object with the movie
    """
    update_user_last_active(user_id)

    # La note doit être un nombre entre 0 et 10
    if not rating.isnumeric() or float(rating) < 0 or float(rating) > 10:
        return make_response(jsonify({"error": "Rating must be a number between 0 and 10"}), 400)

    mutation = """
    mutation {
      update_movie(_id: "%s", rating: %s) {
        id
        title
        director
        rating
      }
    }
    """ % (movie_id, rating)

    response = requests.post("http://movie:3001/graphql", json={"query": mutation})

    if response.status_code == 200:
        response = response.json()["data"]["update_movie"]

        if response:
            return make_response(jsonify(response), 200)

        return make_response(jsonify({"error": "Movie not found"}), 404)

    return make_response(response.json(), response.status_code)


##################### Graphql and gRPC #####################
@app.route("/<user_id>/bookings", methods=['GET'])
def get_bookings(user_id: str) -> Response:
    """
    Get all the bookings of a user

    Notes
    -----
    This function establishes a gRPC connection to the booking service and retrieves all bookings
    associated with the provided user ID.

    If the user is found, the bookings are returned in the response.

    If the user is not found, a 404 error is returned with an appropriate error message.
    :param user_id: id of the user

    :return: Response object with all the bookings
    """
    update_user_last_active(user_id)

    for user in users:
        if user["id"] == user_id:
            channel = grpc.insecure_channel('booking:3002')
            stub = booking_pb2_grpc.BookingStub(channel)
            response = stub.GetBookingByUserId(booking_pb2.UserId(userid=user_id))
            message = json_format.MessageToDict(response)

            if message:
                # Appel à movie pour récupérer les détails des films
                query = """
                {
                  all_movies {
                    id
                    title
                    director
                    rating
                  }   
                }
                """

                response = requests.post("http://movie:3001/graphql", json={"query": query})

                for booking in message["dates"]:
                    for movie in response.json()["data"]["all_movies"]:
                        if movie["id"] in booking["movies"]:
                            booking["movies"].remove(movie["id"])
                            booking["movies"].append(movie)

                # Mettre à jour les données qui n'ont pas été modifiées en les enrobant dans un dict

                for booking in message["dates"]:
                    for movie in booking["movies"]:
                        if type(movie) is str:
                            booking["movies"].remove(movie)
                            booking["movies"].append({"id": movie})

                return make_response(jsonify(message), 200)

    return make_response(jsonify({"error": "User not found"}), 404)

@app.route("/<user_id>/bookings", methods=['POST'])
def add_booking(user_id) -> Response:
    """
    Add a booking to a user

    Notes
    -----
    This function establishes a gRPC connection to the booking service and adds a booking
    associated with the provided user ID.

    The function expects a JSON payload with "date" (in YYYYMMDD format) and "movie" fields.
    It validates the input data and ensures that the movie exists before making the booking

    If the data is valid(i.e., the movie exists and the date is in correct format and in the future),
    the booking is added, and a success message is returned(201).

    If there are validation errors, a 400 error is returned with details about the issues

    If the movie is not found, a 400 error is returned with an appropriate error message

    It also requests a GraphQL query to retrieve the movie details from the movie service and checks if the movie exists.

    Parameters:
    ----------
    :param user_id: id of the user

    :return: Response object with the booking
    """
    update_user_last_active(user_id)

    # Récupération des données de la requête
    data = request.get_json()
    if data is None:
        return make_response(jsonify({"error": "Bad request"}), 400)

    # Vérification de la validité des données
    errors = []

    # String vide ou non présent
    if "date" not in data or data["date"].strip() == "":
        errors.append({"date": "date must not be empty"})
    else:
        # Vérification de la validité de la date YYYYMMDD
        try:
            datetime.datetime.strptime(data["date"], '%Y%m%d')

            # Vérification que la date est dans le futur
            if int(data["date"]) < int(datetime.datetime.now().strftime("%Y%m%d")):
                errors.append({"date": "date must be in the future"})
        except ValueError:
            errors.append({"date": "date must be in the format YYYYMMDD"})

    if "movie" not in data or data["movie"].strip() == "":
        errors.append({"movie": "movie must not be empty"})
    else:
        # Vérification de la validité du film
        query = """
        {
          movie_with_id(_id: "%s") {
            id
          }   
        }
        """ % data["movie"]

        response = requests.post("http://movie:3001/graphql", json={"query": query})

        if response.status_code != 200:
            errors.append({"movie": "movie not found"})

    if errors:
        return make_response(jsonify({"errors": errors, "message": "Invalid data"}), 400)

    channel = grpc.insecure_channel('booking:3002')
    stub = booking_pb2_grpc.BookingStub(channel)
    response = stub.AddBooking(booking_pb2.NewBooking(userid=user_id, date=data["date"], movie=data["movie"]))
    return make_response(jsonify(json_format.MessageToDict(response)), 201)

if __name__ == "__main__":
    print("Server running in port %s" % PORT)
    app.run(host=HOST, port=PORT)
