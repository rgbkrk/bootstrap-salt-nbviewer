#!/usr/bin/env python
# -*- coding: utf-8 -*-


#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''

Bootstrapping the salt minions on Rackspace (using fabric rather than
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

################################################################################
# Master tools
################################################################################

def master_up(key_name, credential_file="~/.rackspace_cloud_credentials"):
    '''
    Create a salt-master on Rackspace
    '''

    # Authenticate with Rackspace, use credential file
    pyrax.set_setting("identity_type", "rackspace")
    pyrax.set_credential_file(os.path.expanduser(credential_file))

    # Shorthand
    cs = pyrax.cloudservers

    # Building Ubuntu 12.04 boxes with 512 MB RAM
    iter_flavors = ifilter(lambda flavor: flavor.ram == 512, cs.flavors.list())
    flavor_512 = iter_flavors.next()
    iter_os = ifilter(lambda img: "Ubuntu 12.04" in img.name, cs.images.list())
    ubu_image = iter_os.next()

    master = cs.servers.create("master.cow", ubu_image.id, flavor_512,
                               key_name=key_name)

    master = pyrax.utils.wait_for_build(master, verbose=True)

    env.hosts = [master.accessIPv4]

    print("Master IP: {}".format(master.accessIPv4))
    return master.accessIPv4

def fullstrap_master():
    bootstrap_salt_master()
    install_pip()
    install_gitpython()
    restart_master()

def bootstrap_salt_master():
    '''
    Bootstraps a salt master
    '''
    run('curl -L http://bootstrap.saltstack.org | sudo sh -s -- -M -N git develop')

def install_pip():
    # Good pip
    run('wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py\
        -O - | python2.7')
    run('curl --show-error --retry 5\
    https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python2.7')

def install_gitpython():
    run('apt-get install git')
    run('pip install GitPython==0.3.2.RC1 --upgrade')

def restart_master():
    run('service salt-master restart')

################################################################################
# Minion tools
################################################################################

def minions_up(key_name, credential_file="~/.rackspace_cloud_credentials"):
    '''
    Creates a specific build of machines and bootstraps salt.

    The credential file can be set via keyword credential_file, and defaults
    to ~/.rackspace_cloud_credentials
    '''

    # Authenticate with Rackspace, use credential file
    pyrax.set_setting("identity_type", "rackspace")
    pyrax.set_credential_file(os.path.expanduser(credential_file))

    # Shorthand
    cs = pyrax.cloudservers

    # Building Ubuntu 12.04 boxes with 512 MB RAM
    iter_flavors = ifilter(lambda flavor: flavor.ram == 512, cs.flavors.list())
    flavor_512 = iter_flavors.next()
    iter_os = ifilter(lambda img: "Ubuntu 12.04" in img.name, cs.images.list())
    ubu_image = iter_os.next()

    domain_template = "{0}{1:02d}.minion.{2}"

    server_names = [domain_template.format(release_type, idx, "cow") for
                    release_type in ("qa", "prod") for idx in xrange(1, 5)]

    # Create homogenous minions (with names as above)
    # This hardcodes the key name to the one I'm using right now.
    minions = map(lambda name: cs.servers.create(name, ubu_image.id,
                  flavor_512, key_name=key_name), server_names)

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
    bootstrap_salt()
    point_minion_at_master(master)
    restart_minion()


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

