from flask import Flask, send_from_directory
from api import register_api
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

FRONTEND_FOLDER = os.path.join(
    BASE_DIR,
    "frontend",
    "dist"
)


app = Flask(
    __name__,
    static_folder=FRONTEND_FOLDER,
    static_url_path=""
)


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


register_api(
    app,
    UPLOAD_FOLDER
)


@app.route("/")
def frontend_index():

    return send_from_directory(
        FRONTEND_FOLDER,
        "index.html"
    )


@app.errorhandler(404)
def frontend_fallback(error):

    return send_from_directory(
        FRONTEND_FOLDER,
        "index.html"
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
