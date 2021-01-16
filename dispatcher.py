import argparse

from manhattan.dispatch import Dispatcher
from werkzeug.serving import run_simple

import manage_app


def create_dispatcher(env):

    # Create and run the application
    return Dispatcher(
        manage_app.create_app(env)
    )


if __name__ == "__main__":

    # Parse the command-line arguments
    parser = argparse.ArgumentParser(description='Application dispatcher')
    parser.add_argument(
        '-p',
        '--port',
        action='store',
        default=5001,
        dest='port',
        required=False,
        type=int
    )
    args = parser.parse_args()

    # Initialize the dispatcher app
    dispatcher = create_dispatcher('local')

    # Run the dispatcher using `run_simple` if initialized for local development
    run_simple(
        'localhost',
        args.port,
        dispatcher,
        use_debugger=dispatcher.app.config['DEBUG'],
        use_reloader=dispatcher.app.config['DEBUG']
    )
