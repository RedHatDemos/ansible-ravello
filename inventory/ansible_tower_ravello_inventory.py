#!/usr/bin/python

'''
Ravello external inventory script
==================================================
Generates inventory that Ansible can understand by making an API request to Ravello.
Modeled after https://raw.githubusercontent.com/jameslabocki/ansible_api/master/python/ansible_tower_cloudforms_inventory.py

Required: Ravello Python SDK https://github.com/ravello/python-sdk
Useful: https://www.ravellosystems.com/ravello-api-doc/

Notes: In my testing, with >200 applications and ~1,000 virtual machines this took 30 seconds to execute.
       If the get_applications call in the Ravello Python SDK supported dumping design information this could be dramatically reduced.

jlabocki <at> redhat.com or @jameslabocki on twitter
'''

import os
import re
import argparse
import ConfigParser
import requests
import json
from argparse import ArgumentParser
from ravello_sdk import *
from common import *

class RavelloInventory(object):

    def _empty_inventory(self):
        return {"_meta" : {"hostvars" : {}}}

    def __init__(self):
        ''' Main execution path '''

        # Inventory grouped by instance IDs, tags, security groups, regions,
        # and availability zones
        self.inventory = self._empty_inventory()

        # Index of hostname (address) to instance ID
        self.index = {}

        # Read CLI arguments
        self.read_settings()
        self.parse_cli_args()

        # If --list is set then run get_apps_all
        if self.args.list is True:
          self.get_apps_all()

        # If --app is set then run get_app with ID of application 
        if self.args.app is not None:
          self.get_app()

    def parse_cli_args(self):
        ''' Command line argument processing '''

        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on Ravello')
        parser.add_argument('--app', action='store',
                           help='Get the groups and hostname from a specific application specifying the app name')
        parser.add_argument('--list', action='store_true', default=False,
                           help='List all app names (default: False)')
        self.args = parser.parse_args()

    def read_settings(self):
        ''' Reads the settings from the ravello.ini file '''

        config = ConfigParser.SafeConfigParser()
        config_paths = [
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ravello.ini'),
            "/etc/ansible/ravello.ini",
        ]

        env_value = os.environ.get('RAVELLO_INI_PATH')
        if env_value is not None:
            config_paths.append(os.path.expanduser(os.path.expandvars(env_value)))

        config.read(config_paths)

        self.ravello_username, self.ravello_password  = get_user_credentials(None)
        if not self.ravello_username or not self.ravello_password:
                exit(1)

        # Ravello Username
        #if config.has_option('ravello', 'username'):
        #    self.ravello_username = config.get('ravello', 'username')
        #else:
        #    self.ravello_username = "none"
#
#        # Ravello Password
#        if config.has_option('ravello', 'password'):
#            self.ravello_password = config.get('ravello', 'password')
#        else:
#            self.ravello_password = "none"

    def get_apps_all(self):
        #Connect to Ravello
        client = connect(self.ravello_username, self.ravello_password)
        if not client:
                exit (1)

        apps = client.get_applications()

        names = []
        for app in apps:
          #Only get the published apps
          if app['published']:
            myname = (json.dumps(app['name']))
            names.append(myname)
        for name in names:
          print name 


    def get_app(self):
        #Connect to Ravello
        myappname = self.args.app
        client = connect(self.ravello_username, self.ravello_password)
        if not client:
                exit (1)

        apps = client.get_applications()

        myappid = ""

        for app in apps:
          #Only get the published apps
          if app['published']:
            if str(app['name']) == myappname:
              myappid = app['id']

        #First, define empty lists for the the tags, groups, subgroups for tags/vms, and the formatted list for tower.
        tags = {}

        app = client.get_application(myappid, aspect="deployment")

        if app['deployment']:
          appname = app['name']
          vmsFlag = True if "vms" in app["deployment"] else False
          if vmsFlag == True:
            vms = app['deployment']['vms']
            for vm in vms:
              if 'externalFqdn' in vm:
                hostname = vm['externalFqdn']
              else:
                hostnames = vm['hostnames']
                hostname = hostnames[0]
              desc = vm['description']
              for line in desc.splitlines():
                if re.match("^tag:", line):
                  t = line.split(':')
                  tag = t[1]
                  if tag in tags.keys():
                    tags[tag].append(hostname)
                  else:
                    tags[tag] = [hostname]
                    
        print json.dumps(tags, indent=5)  

#Run the script
RavelloInventory()
