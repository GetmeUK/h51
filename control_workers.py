import argparse
import os
import socket
import subprocess
import sys
import time
import uuid

import psutil
from flask import Config
import redis
import redis.sentinel

from workers.workers import AssetWorker
from swm import monitors


site_path = "/sites/h51"
logfile_path = os.path.join(site_path, 'logs', 'workers_debug.log')
spawn_command = [
    '/usr/bin/nohup', 
    '/sites/h51/venv/bin/python', 
    '/sites/h51/asset_worker.py', 
    '--env', 
    'production'
]
command_signature = ' '.join(['python', 'asset_worker.py', '--env', 'production'])


class ControlWorkers(object):

    def __init__(self, args):
        self.env = args.env
        self.action = args.action
        self.kill_delay = args.kill_delay
        self.conn = None

        # Load settings                                                                                                                                       
        self.config = Config(os.path.dirname(os.path.realpath(__file__)))
        # There may be overiding settings specific to the server we are running on                                                                             
        servername = socket.gethostname().split('.')[0]
        if servername and os.path.isfile(f'settings/workers/{self.env}_{servername}.py'):
            self.config.from_object(f'settings.workers.{self.env}_{servername}.Config')
        else:
            self.config.from_object(f'settings.workers.{self.env}.Config')


        # Redis                                                                                                                                               
        if self.config['REDIS_USE_SENTINEL']:
            sentinel = redis.sentinel.Sentinel(
                self.config['REDIS_ADDRESS'],
                db=self.config['REDIS_DB'],
                password=self.config['REDIS_PASSWORD'],
                decode_responses=True
            )
            self.conn = sentinel.master_for(self.config['REDIS_SENTINEL_MASTER'])

        else:
            self.conn = redis.StrictRedis(
                host=self.config['REDIS_ADDRESS'][0],
                port=self.config['REDIS_ADDRESS'][1],
                db=self.config['REDIS_DB'],
                password=self.config['REDIS_PASSWORD'],
                decode_responses=True
            )

    def run(self):
        if self.action == 'status':
            self.status_workers()
        elif self.action == 'spawn':
            self.spawn_worker()
        elif self.action == 'stop':
            self.stop_workers()
        elif self.action == 'respawn':
            self.stop_workers()
            self.spawn_worker()

    def spawn_worker(self):
        """This will spawn an initial worker.
        More workers will be spawned as needed within limits set in config.
        """
        # Check we don't already have workers running
        procs = self.get_worker_processes()
        if procs:
            sys.exit(
                "Not spawning new worker because running worker process(es) found "
                f"pids: {' '.join([p.pid for p in procs])}"
            )
        r = subprocess.Popen(
            spawn_command, 
            stdout=open(logfile_path, 'a'), 
            stderr=open(logfile_path, 'a')
        )
        if r.returncode:
            print(f'Failed to spawn worker, return code {r.returncode}')
            print(f'There may be more info in {logfile_path}')
            sys.exit(1)

    def stop_workers(self):
        monitors.shutdown_workers(self.conn, AssetWorker, uuid.getnode())

        # Allow time for monitors to kill themselves
        while self.kill_delay > 0 and self.get_worker_processes():
            time.sleep(1)
            self.kill_delay -= 1

        # Forcibly kill any that remain as 
        procs =  [p for p in psutil.process_iter() if command_signature in ' '.join(p.cmdline())]
        if not procs:
            return
        for p in alive:
            print(f"forcibly killing {p.pid}")
            p.kill()
        sys.exit(1)

    def respawn_workers(self):
        self.stop_workers()
        self.spawn_worker

    def status_workers(self):
        procs = self.get_worker_processes()
        print(f"{len(procs)} workers running")
        if procs:
            sys.exit(0)
        else:
            sys.exit(1)

    def get_worker_processes(self):
        return [p for p in psutil.process_iter() if command_signature in ' '.join(p.cmdline())]



# Main                                                                                                                                                        
if __name__ == '__main__':

    # Parse command-line arguments                                                                                                                            
    parser = argparse.ArgumentParser(description='API application')
    parser.add_argument(
        '-e',
        '--env',
        choices=['staging', 'production'],
        default='',
        dest='env',
        required=False
        )
    parser.add_argument(
        '-a',
        '--action',
        choices=['spawn', 'stop', 'status', 'respawn'],
        default='status',
        dest='action',
        required=False
        )
    parser.add_argument(
        '-k',
        '--kill-delay',
        default=10,
        dest='kill_delay',
        required=False,
        type=int
        )
    args = parser.parse_args()

    # Create the application                                                                                                                                  
    controller = ControlWorkers(args)

    controller.run()
