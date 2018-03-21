
import os
import sys
import base64
import getpass
import logging
import logging.handlers

from ravello_sdk import *

def get_credentials():
        with open(os.path.expanduser("~/.ravello_login"),"r") as pf:
                username = pf.readline().strip()
                encrypted_password = pf.readline().strip()
        password = base64.b64decode(encrypted_password).decode()
        return username,password

def get_blueprint_id(blueprint_name,client):
        blueprint_id=0
        for blueprint in client.get_blueprints():
                if blueprint['name'].lower() == blueprint_name.lower():
                        blueprint_id = blueprint['id']
                        break
        return blueprint_id

def main():
        username, password = get_credentials()
        client = RavelloClient(username, password)
        print(get_blueprint_id(sys.argv[1], client))
        
main()
