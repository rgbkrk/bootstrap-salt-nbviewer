bootstrap-salt-nbviewer
=======================

Bootstrapping salt for nbviewer

# fabfile

The fabric file bootstraps a salt master and salt minions on Rackspace.

## Prerequisites (local)

Make a virtualenv to install requisite python packages and install them via requirements.txt

```
$ mkvirtualenv boots
(boots) $ pip install -r requirements.txt
```

Create a credential file for Rackspace (to be used with the pyrax module)

```
[rackspace_cloud]
username=
api_key=
```

## Getting up and running

First launch the master (and fully bootstrap the salt install):
```
$ fab master_up:key_name=main,credential_file=~/.rax_creds fullstrap_master
```

Grab the IP address of the master for the next call on the minions

```
$ fab minions_up:key_name=main fullstrap_minions:master=<ip from master up>
```

After this all, you can login to the salt master and accept keys from each of the minions

```
# salt-key -L
Accepted Keys:
Unaccepted Keys:
prod01.iad.ipython.org
prod02.iad.ipython.org
qa01.iad.ipython.org
qa02.iad.ipython.org
Rejected Keys:
```

Accepting all the keys (**Note: this blindly accepts them, fingerprints should be checked from each minion**)
```
# salt-key -A
```

## List of commands

Available commands:

    apt_update              Runs apt-get update and upgrade
    bootstrap_salt          Uses the salt bootstrap script (from bootstrap.saltstack.org) to install a
    bootstrap_salt_master   Bootstraps a salt master
    fullstrap_master        Runs through apt_update, installing curl, using salt bootstrap (for
    fullstrap_minions       Install saltstack, set master, restart the salt-minion daemon
    ifilter                 ifilter(function or None, sequence) --> ifilter object
    install_curl            Installs curl
    install_gitpython       Installs gitpython and dependencies
    install_pip             Installs pip using the ez_setup script (from bitbucket.org/pypa/setuptools)
    master_up               Create a salt-master on Rackspace
    minions_up              Creates a specific build of machines and bootstraps salt.
    point_minion_at_master  Simply writes the master for this minion at /etc/salt/minion
    restart_master          Restarts the salt master
    restart_minion          Restart a salt minion

