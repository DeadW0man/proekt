from os import getenv

from flask import Flask

from api.http import api_bp
from db.db import close_db, prepare_tables

solaris_app = Flask('solaris')
solaris_app.register_blueprint(api_bp)
solaris_app.teardown_appcontext(close_db)


def run_app() -> None:
    solaris_app.run(
        host=getenv('SOLARIS_HOST', '0.0.0.0'),
        port=int(getenv('SOLARIS_PORT', '5000')),
        debug=getenv('SOLARIS_DEBUG', '1') == '1'  # в проде выставить 0
    )


if __name__ == '__main__':
    with solaris_app.app_context():
        prepare_tables()
    run_app()
