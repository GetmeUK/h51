import argparse

from workers.workers import AssetWorker


if __name__ == '__main__':

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Asset worker')
    parser.add_argument(
        '-e',
        '--env',
        choices=['staging', 'local', 'production', 'test'],
        default='local',
        dest='env',
        required=False
    )
    parser.add_argument(
        '-i',
        '--idle-lifespan',
        default='0',
        dest='idle_lifespan',
        required=False,
        type=int
    )
    args = parser.parse_args()

    worker = AssetWorker(args.env, args.idle_lifespan)
    worker.start()
