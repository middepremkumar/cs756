import logging
import os
from flask import Flask, render_template
from flask_cors import CORS

from api.inventory import inventory_bp


def create_app():
    app = Flask(__name__)
    CORS(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    app.register_blueprint(inventory_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
