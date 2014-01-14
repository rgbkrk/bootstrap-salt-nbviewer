#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''

Bootstrapping salt minions on Rackspace (using fabric rather than
salt-cloud).

This is not the most effective way to do this, but it gets it done.

For instance, we could be bootstrapping servers while others are still being
built by Rackspace. In the end, it doesn't matter much.

To get up and running, use

$ fab master_up:key_name=main,credential_file=~/.rax_creds fullstrap_master

$ fab minions_up:key_name=main fullstrap_minions:master=<ip from master up>

minions_up will set env.hosts (for other fabric calls).

If you want to use other calls as a standalone, be sure
to set the hosts when calling them.

$ fab -H 67.207.156.15,67.207.156.147,67.207.155.4 restart_minion

'''

import os
from itertools import ifilter

import fabric.api
from fabric.api import parallel
from fabric.api import env, run
from fabric.contrib import files
from fabric.context_managers import settings

import pyrax

env.user = 'root'
env.key_filename = os.path.expanduser("~/.ssh/id_rsa")
env.forward_agent = True

#default_image = u'62df001e-87ee-407c-b042-6f4e13f5d7e1' # | Ubuntu 13.04
default_image = u'df27d481-63a5-40ca-8920-3d132ed643d9' # Ubuntu 13.10
default_flavor = u'performance1-8'

default_layout = {
        "master":
            {"image": u'df27d481-63a5-40ca-8920-3d132ed643d9',
             "flavor": u'performance1-4',
             "hostname": u'master'}
        "minions": [ {"image": u'df27d481-63a5-40ca-8920-3d132ed643d9',
                      "flavor": u'performance1-8',
                      "hostname": name} for name in
                            ("qa01.nbviewer.ipython.org",
                             "qa02.nbviewer.ipython.org",
                             "prod01.nbviewer.ipython.org",
                             "prod02.nbviewer.ipython.org")
                   ]
}


################################################################################
# Master tools
################################################################################

def master_up(key_name, credential_file="~/.rackspace_cloud_credentials",
              image=default_layout["master"]["image"],
              flavor=default_layout["master"]["flavor"],
              region="IAD"):
    '''
    Create a salt-master on Rackspace

    Alternatively create the master using nova
    '''

    # Authenticate with Rackspace, use credential file
    pyrax.set_setting("identity_type", "rackspace")
    pyrax.set_credential_file(os.path.expanduser(credential_file))

    # Shorthand
    cs = pyrax.connect_to_cloudservers(region=region)

    master = cs.servers.create("master.iad.ipython.org", image, flavor,
                               key_name=key_name)

    master = pyrax.utils.wait_for_build(master, verbose=True)

    env.hosts = [master.accessIPv4]

    print(master.networks)

    print("Master IP: {}".format(master.accessIPv4))

    return master.accessIPv4

def fullstrap_master():
    '''
    Runs through apt_update, installing curl, using salt bootstrap (for
    master), installs pip, gitpython, restarts master.
    '''
    apt_update()
    install_curl()
    bootstrap_salt_master()
    install_pip()
    install_gitpython()
    place_master_configuration()
    restart_master()
    run("apt-get -y install vim")

def place_master_configuration():
    files.upload_template("etc/salt/master", "/etc/salt/master")
    

@parallel
def install_curl():
    '''
    Installs curl
    '''
    run("apt-get -y install curl")

@parallel
def apt_update():
    '''
    Runs apt-get update and upgrade
    '''
    run('apt-get -y update')
    run('apt-get -y upgrade')

def bootstrap_salt_master():
    '''
    Bootstraps a salt master
    '''
    run('curl -L http://bootstrap.saltstack.org | sudo sh -s -- -M -N git develop')

def install_pip():
    '''
    Installs pip using the ez_setup script (from bitbucket.org/pypa/setuptools)
    '''
    # Good pip
    run('wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py\
        -O - | python2.7')
    run('curl --show-error --retry 5\
    https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python2.7')

def install_gitpython():
    '''
    Installs gitpython and dependencies
    '''
    run('apt-get install git')
    run('pip install GitPython==0.3.2.RC1 --upgrade')

def restart_master():
    '''
    Restarts the salt master
    '''
    run('service salt-master restart')

################################################################################
# Minion tools
################################################################################

def minions_up(key_name, credential_file="~/.rackspace_cloud_credentials",
               layout=default_layout, region="IAD"):
    '''
    Creates a specific build of machines and bootstraps salt.

    The credential file can be set via keyword credential_file, and defaults
    to ~/.rackspace_cloud_credentials
    '''

    # Authenticate with Rackspace, use credential file
    pyrax.set_setting("identity_type", "rackspace")
    pyrax.set_credential_file(os.path.expanduser(credential_file))

    # Shorthand
    cs = pyrax.connect_to_cloudservers(region=region)

    minions = []

    for minion in layout["minions"]:
        minions.append(cs.servers.create(minion["hostname"],
                                         minion["image"],
                                         minion["flavor"]
                                         key_name=key_name))

    # Make sure all the minions are done before we move on to fabric runs
    minions = [pyrax.utils.wait_for_build(minion, verbose=True)
               for minion in minions]

    env.hosts = [str(minion.accessIPv4) for minion in minions]
    print(env.hosts)


@parallel
def fullstrap_minions(master):
    '''
    Install saltstack, set master, restart the salt-minion daemon

    $ fab fullstrap_minions:master=127.0.0.1
    '''
    apt_update()
    install_curl()
    bootstrap_salt()
    point_minion_at_master(master)
    restart_minion()
    run('apt-get -y install vim') # Sneaking this in to make life better


@parallel
def bootstrap_salt():
    '''
    Uses the salt bootstrap script (from bootstrap.saltstack.org) to install a
    salt-minion and run it as a daemon
    '''
    run("curl -L http://bootstrap.saltstack.org | sh -s -- git develop")

@parallel
def point_minion_at_master(master):
    '''
    Simply writes the master for this minion at /etc/salt/minion

    $ fab point_minion_at_master:master=127.0.0.1
    '''
    run("echo 'master: {}' > /etc/salt/minion".format(master))

@parallel
def restart_minion():
    '''
    Restart a salt minion
    '''
    run("service salt-minion restart")

