"""
Fabric is used to deploy changes and run tasks on the remote staging and
production environments.
"""

import json
import os
import shutil
import zipfile

import botocore.exceptions
import botocore.session
from fabric import Connection
from fabric import SerialGroup as Group
from fabric import task
from invoke.exceptions import Exit
from patchwork.files import exists
from patchwork.transfers import rsync


# -- Defaults --

settings = {

    # The asset folders for the application
    'asset_paths': ['manage'],

    # The branch of the repository this environment uses
    'branch': 'develop',

    # The environment the fabric tas will execute in
    'env': 'local',

    # Directory on the remote server the application is installed
    'home': '',

    # The remote hosts for the project (the first host must be the primary
    # host).
    'hosts': Group('localhost'),

    # Path to nginx
    'nginx_path': '',

    # The user that owns the project
    'project_user': 'h51',

    # The code repository
    'repo': '',

    # A list of manage commands that should run on all hosts not just the
    # primary.
    'run_everywhere_manage_commands': [],

    # Path to supervisor
    'supervisor_path': '',

    # The prefix for supervisor programs
    'supervisor_prefix': 'h51',

}


# -- Environment tasks --

@task(aliases=['stag'])
def staging(ctx):
    """Set up the staging environment"""

@task(aliases=['prod'])
def production(ctx):
    """Set up the production environment"""


# -- User tasks --

@task
def as_root(ctx):
    """Instruct fabric to use the root user"""
    for conn in settings['hosts']:
        conn.user = 'root'

        # Reconnect as the root user
        conn.close()
        conn.open()


# -- Setup tasks --

@task
def init(ctx):
    """Initialize a new instance of the application"""

    if settings['env'] == 'local':

        # Setting up a git repository isn't required (the fabfile wouldn't
        # exist if this hadn't already been done).

        # Check that a virtual environment doesn't exist
        if os.path.exists('venv/bin/python3.7'):
            raise Exit('Virtual environment already exist')

        else:
            conn = settings['hosts'][0]
            conn.local('python3.7 -m venv venv', replace_env=False)

    else:

        for conn in settings['hosts']:
            with conn.cd(settings['home']):

                # Check that a git repo doesn't exists
                if exists(conn, '.git'):
                    print('Repository already exist')

                else:
                    # Add the repo
                    repo = settings['repo']
                    conn.run('git init')
                    conn.run(f'git remote add origin {repo}')
                    conn.run('git fetch origin')

                # Check that a virtual environment doesn't exist
                if exists(conn, 'venv/bin/python3.7'):
                    print('Virtual environment already exist')

                else:
                    conn.run('python3.7 -m venv venv')

@task
def nginx(ctx):
    """Configure nginx"""

    # Build the config filepaths
    path = os.path.join(
        settings['nginx_path'],
        settings['project_user'] + '.conf'
    )

    backup_path = os.path.join(
        settings['nginx_path'],
        settings['project_user'] + '.conf.backup'
    )

    if settings['env'] == 'local':
        conn = settings['hosts'][0]

        # Make sure theirs an entry in the hosts file
        entry = 'h51.local'
        api_entry = 'api.h51.local'
        with open('/etc/hosts', 'r') as f:
            hosts = f.read()

        # Check if the hosts file contains entries
        if (' ' + entry) not in hosts:
            conn.local(
                f'sudo echo "127.0.0.1 {entry}" | sudo tee --append /etc/hosts',
                replace_env=False
            )

        if (' ' + api_entry) not in hosts:
            conn.local(
                (
                    f'sudo echo "127.0.0.1 {api_entry}" | '
                    'sudo tee --append /etc/hosts'
                ),
                replace_env=False
            )

        # Make back up of any existing config
        if os.path.exists(path):
            conn.local(f'sudo cp {path} {backup_path}')

        # Copy the nginx config
        conn.local(f'sudo cp root/nginx/local.conf {path}', replace_env=False)

        # Test the config
        if conn.local('sudo nginx -t', replace_env=False, warn=True):

            # Success - restart nginx
            conn.local('sudo service nginx restart', replace_env=False)

        else:

            # Failed - restore the original settings
            if os.path.exists(backup_path):
                conn.local(f'sudo cp {backup_path} {path}', replace_env=False)

            else:
                conn.local(f'sudo rm {path}', replace_env=False)

        # Remove any back up created
        if os.path.exists(backup_path):
            conn.local('sudo rm ' + backup_path, replace_env=False)

    else:

        for conn in settings['hosts']:

            # Ensure log folders are set up
            project_user = settings['project_user']
            logs_path = f'/sites/{project_user}/logs'

            if not exists(conn, logs_path):
                conn.run(f'mkdir {logs_path}')
                conn.run(f'chown {project_user}:{project_user} {logs_path}')
                conn.run(f'chmod 755 /sites/{project_user}')

            # Make a back of any existing config
            if exists(conn, path):
                conn.run(f'cp {path} {backup_path}')

            # Copy the nginx config
            with conn.cd(settings['home']):
                env = settings['env']
                conn.run(f'cp root/nginx/{env}.conf {path}')

            # Test the config
            if conn.run('nginx -t'):

                # Success - restart nginx
                conn.run('service nginx restart')

            else:

                # Failed - restore the original settings
                if exists(conn, backup_path):
                    conn.run(f'cp {backup_path} {path}')

                else:
                    conn.run(f'rm {path}')

            # Remove any back up created
            if os.path.exists(backup_path):
                conn.run(f'rm {backup_path}')

@task(iterable=['paths'])
def npm(ctx, paths):
    """Install node models"""

    if not paths:
        paths = settings['asset_paths']

    if settings['env'] == 'local':
        conn = settings['hosts'][0]

        for path in paths:
            with conn.cd(os.path.join('webpack', path)), local_node(conn):
                conn.local('npm install', replace_env=False)

    else:
        raise Exit(
            'Assets are compiled locally and node is not used on remote '
            'environments.'
        )

@task
def pip(ctx):
    """Install python packages"""

    if settings['env'] == 'local':
        conn = settings['hosts'][0]
        conn.local(
            'venv/bin/pip install -r requirements.txt',
            replace_env=False
        )

    else:
        for conn in settings['hosts']:
            with conn.cd(settings['home']):
                conn.run('venv/bin/pip install -r requirements.txt')

@task
def supervisor(ctx):
    """Configure supervisor"""

    # Build the config filepaths
    path = os.path.join(
        settings['supervisor_path'],
        settings['project_user'] + '.conf'
    )

    backup_path = os.path.join(
        settings['supervisor_path'],
        settings['project_user'] + '.conf.backup'
    )

    if settings['env'] == 'local':
        raise Exit(
            'Supervisor isn\'t typically used on local setups and so it\'s '
            'configuration isn\'t supported in the local environment.'
        )

    else:

        for conn in settings['hosts']:

            supervisor_path = conn\
                .run('which supervisorctl', hide=True)\
                .stdout\
                .strip()

            # Make a back of any existing config
            if exists(conn, path):
                conn.run(f'cp {path} {backup_path}')

            with conn.cd(settings['home']):
                env = settings['env']
                conn.run(f'cp root/supervisor/{env}.conf {path}')

            # Attempt to re-read the configuration
            if conn.run(f'{supervisor_path} reread', warn=True):

                # Success - update and start the application
                conn.run(f'{supervisor_path} update')

                # This operation may fail (as the app may already have
                # restarted), we want the warning message to appear in case
                # there's another reason for the failure.
                supervisor_prefix = settings['supervisor_prefix']
                conn.run(
                    f'{supervisor_path} start {supervisor_prefix}_app',
                    warn=True
                )

            else:
                # Failed - restore the original settings
                if conn.exists(backup_path):
                    conn.run(f'cp {backup_path} {path}')

                else:
                    conn.run(f'rm {backup_path}')

            # Remove any back up created
            if exists(conn, backup_path):
                conn.run(f'rm {backup_path}')


# -- Build task --

@task(iterable=['paths'])
def assets(ctx, paths):
    """Build static assets for the application (JS, CSS, Images, etc.)"""

    if not paths:
        paths = settings['asset_paths']

    if settings['env'] == 'local':

        if len(paths) > 1:
            raise Exit(
                'Only one asset path can be set when compiling local assets.'
            )

        conn = settings['hosts'][0]

        with conn.cd(os.path.join('webpack', paths[0])), local_node(conn):
            conn.local('npm run start', pty=True, replace_env=False)

    else:

        for path in paths:

            # Check we've using the correct branch for deployment
            branch = settings['branch']
            current_branch = settings['hosts'][0].local(
                'git rev-parse --abbrev-ref HEAD',
                replace_env=False
            ).stdout.strip()

            if current_branch != branch:
                raise Exit(
                    f'You must be on the *{branch}* branch to perform this '
                    'task. Important! Make sure your changes are merged into '
                    'the correct branch.'
                )

            # Only compile the assets once
            conn = settings['hosts'][0]
            with conn.prefix('cd ' + os.path.join('webpack', path)):

                # Remove the existing static-assest file
                if os.path.exists('static-assets.json'):
                    conn.local('rm static-assets.json', replace_env=False)

                # Compile the assets for the set environment
                with local_node(conn):
                    env = settings['env']
                    conn.local(f'npm run {env}', replace_env=False)

            # Upload the asset manifest and the email CSS
            for conn in settings['hosts']:
                home = settings['home']
                with conn.cd(settings['home']):

                    # Manifest file
                    conn.put(
                        f'webpack/{path}/static-assets.json',
                        f'webpack/{path}/static-assets.json'
                    )

                    # Email CSS
                    email_path = f'webpack/{path}/emails/{path}.css'
                    if os.path.exists(email_path):

                        # Check the directory exists
                        if not exists(conn, f'webpack/{path}/emails/'):
                            with conn.cd(f'webpack/{path}/'):
                                conn.run('mkdir emails')

                        conn.put(email_path, email_path)

@task
def deploy(ctx):
    """Deploy changes in the code repository to the remote server"""

    if settings['env'] == 'local':

        # Check that a git repo exists
        if not os.path.exists('.git'):
            raise Exit(
                'Repository does not exist. Use `init` command to create the '
                'repo.'
            )

        conn = settings['hosts'][0]

        # Checkout to the relevant branch
        branch = settings['branch']
        conn.local('git fetch', replace_env=False)
        conn.local(f'git checkout {branch}', replace_env=False)

        # Pull down the changes from the repo
        conn.local('git pull', replace_env=False)

    else:
        for conn in settings['hosts']:
            with conn.cd(settings['home']):

                # Check that a git repo exists
                if not exists(conn, '.git'):
                    raise Exit(
                        'Repository does not exist. Use `init` command to '
                        'create the repo.'
                    )

                # Checkout to the relevant branch
                branch = settings['branch']
                conn.run('git fetch')
                conn.run(f'git checkout {branch}')

                # Pull down the changes from the repo
                conn.run('git pull')

@task
def emails(ctx, path=None):
    """Build static assets for emails"""

    if not settings['env'] == 'local':
        raise Exit('Emails can only be run locally')

    if path not in settings['asset_paths']:
        raise Exit('Not a valid `path`')

    conn = settings['hosts'][0]
    with conn.cd(os.path.join('webpack', path)):

        with local_node(conn):
            conn.local('npm run email', pty=True, replace_env=False)

@task
def manage(ctx, command=None):
    """Run a manage command"""

    if settings['env'] == 'local':
        conn = settings['hosts'][0]
        env = settings['env']

        conn.config.run.env = {'FLASK_APP': f'commands:create_app("{env}")'}
        with conn.prefix('source venv/bin/activate'):
            conn.local(f'flask {command}', pty=True, replace_env=False)

    else:

        command_name = command.split(' ', 1)[0]
        env = settings['env']
        export = f'export FLASK_APP="commands:create_app(\'{env}\')"'

        if command_name in settings['run_everywhere_manage_commands']:
            for conn in settings['hosts']:
                with conn.prefix(export):
                    with conn.prefix('source venv/bin/activate'):
                        conn.run(f'flask {command}', pty=True)

        else:
            conn = settings['hosts'][0]
            with conn.prefix(export):
                with conn.prefix('source venv/bin/activate'):
                    conn.run(f'flask {command}', pty=True)


# -- Server tasks ---

@task
def cycle(ctx):
    """Cycle the public and manage apps"""

    if settings['env'] == 'local':
        raise Exit(
            'In the local environment the app is run using a daemon, to '
            'cycle the app use `Ctrl+C` and run `fab start`.'
        )

    else:
        for conn in settings['hosts']:
            conn.run(supervisor_manage_cmd(conn, 'restart'))

@task
def start(ctx):
    """Start the public and manage apps"""

    if settings['env'] == 'local':
        conn = settings['hosts'][0]
        conn.local(
            'venv/bin/python dispatcher.py',
            pty=True,
            replace_env=False
        )

    else:
        for conn in settings['hosts']:
            conn.run(supervisor_manage_cmd(conn, 'start'))

@task
def stop(ctx):
    """Stop the public and manage apps"""

    if settings['env'] == 'local':
        raise Exit(
            'In the local environment the app is run using a daemon, to quit '
            'the app use `Ctrl+C`.'
        )

    else:
        for conn in settings['hosts']:
            conn.run(supervisor_manage_cmd(conn, 'stop'))


# -- API tasks --

@task
def cycle_api(ctx):
    """Cycle the API app"""

    if settings['env'] == 'local':
        raise Exit(
            'In the local environment the API is run using a daemon, to '
            'cycle the API use `Ctrl+C` and run `fab start-api`.'
        )

    else:
        for conn in settings['hosts']:
            conn.run(supervisor_api_cmd(conn, 'restart'))

@task
def start_api(ctx):
    """Start the API app"""

    if settings['env'] == 'local':
        conn = settings['hosts'][0]
        conn.local('venv/bin/python api_app.py', pty=True, replace_env=False)

    else:
        for conn in settings['hosts']:
            conn.run(supervisor_api_cmd(conn, 'start'))

@task
def stop_api(ctx):
    """Stop the API app"""

    if settings['env'] == 'local':
        raise Exit(
            'In the local environment the API is run using a daemon, to quit '
            'the app use `Ctrl+C`.'
        )

    else:
        for conn in settings['hosts']:
            conn.run(supervisor_api_cmd(conn, 'stop', 'api'))

# -- Worker tasks --

@task
def cycle_workers(ctx):
    """Cycle the workers"""

    if settings['env'] == 'local':
        raise Exit(
            'In the local environment use spawn_asset_worker '
        )

    else:
        for conn in settings['hosts']:
            conn.run(f'/etc/cron.scripts/h51_stop_workers {settings["env"]}')
            conn.run(f'/etc/cron.scripts/h51_spawn_worker {settings["env"]}')


@task
def stop_workers(ctx):
    """Stop the workers"""

    if settings['env'] == 'local':
        raise Exit(
            'In the local environment use kill to quit the workers '
        )

    else:
        for conn in settings['hosts']:
            conn.run(f'/etc/cron.scripts/h51_stop_workers {settings["env"]}')


@task(aliases=['spawn_worker'])
def spawn_asset_worker(ctx):
    """Spawn an asset worker"""

    if settings['env'] == 'local':
        conn = settings['hosts'][0]
        conn.local(
            'venv/bin/python asset_worker.py 2>/dev/null >/dev/null &',
            replace_env=False
        )

    else:
        for conn in settings['hosts']:
            conn.run(f'/etc/cron.scripts/h51_spawn_worker {settings["env"]}')


# -- Contexts --

def local_node(conn):
    """Node environment context"""
    return conn.prefix(
        'export MANPATH=":." && source ~/.nvm/nvm.sh && nvm use'
    )


# -- Utils --

def supervisor_api_cmd(conn, cmd):
    """Return the required string to call the given command"""

    supervisor_path = conn.run('which supervisorctl', hide=True).stdout.strip()
    supervisor_prefix = settings['supervisor_prefix']

    return f'{supervisor_path} {cmd} {supervisor_prefix}_api'

def supervisor_manage_cmd(conn, cmd):
    """Return the required string to call the given command"""

    supervisor_path = conn.run('which supervisorctl', hide=True).stdout.strip()
    supervisor_prefix = settings['supervisor_prefix']

    return f'{supervisor_path} {cmd} {supervisor_prefix}_manage'

