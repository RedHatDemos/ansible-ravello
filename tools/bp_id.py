
import os
import json
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

def main():
        username, password = get_credentials()
        client = RavelloClient(username, password)
        app = client.get_application(sys.argv[1])
        print(json.dumps(app, indent=2))
        
main()
