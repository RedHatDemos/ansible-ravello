#!/usr/bin/python

# (c) 2015, ravellosystems
# 
# author zoza
#
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

# TODO
# multiple IPs per nic
# tags/groups

import random, string

try:
    from ravello_sdk import *
    HAS_RAVELLO_SDK = True
except ImportError:
    HAS_RAVELLO_SDK = False

except ImportError:
    print "failed=True msg='ravello sdk required for this module'"
    sys.exit(1)

from ravello_cli import get_diskimage

from ansible.module_utils.ravello_utils import *

DOCUMENTATION = '''
---
module: ravello_app
short_description: Create/delete/start/stop an application in ravellosystems
description:
     - Create/delete/start/stop an application in ravellosystems and wait for it (optionally) to be 'running'
     - list state will return a fqdn list of exist application hosts with their external services
     - blueprint state will create a blueprint from an existing app (must provide blueprint_name)
options:
  state:
    description:
     - Indicate desired state of the target.
    default: present
    choices: ['design', 'present', 'started', 'absent', 'stopped','list','blueprint']
  username:
     description:
      - ravello username
  password:
    description:
     - ravello password
  service_name: 
  	description:
     - Supplied Service name for list state 
    default: ssh
  name:
    description:
     - application name
  description:
    description:
     - application description
  blueprint_id:
    description:
     - create app, based on this blueprint
  #publish options
  cloud:
    description:
     - cloud to publish
  region:
    description:
     - region to publish
  publish_optimization:
    default: cost
    choices: ['cost', 'performance']
  application_ttl:
    description:
     - application autostop in mins
    default: -1 # never
  wait
    description:
     - Wait for the app to be in state 'running' before returning.
    default: True
    choices: [ True, False ]
  wait_timeout:
    description:
     - How long before wait gives up, in seconds.
    default: 600
  blueprint_name:
    description:
     - Specify a name for a new blueprint based on existing app
  blueprint_description:
    description:
     - Description of new blueprint 
  app_template:
    description:
     - Path to a YML file that defines an application infrastructure then creates a blueprint for further processing with follow-on playbooks.  Must use state=design
  cost_bucket:
    description:
     - Path to a YML file that defines an application infrastructure then creates a blueprint for further processing with follow-on playbooks.  Must use state=design
'''

EXAMPLES = '''
# Create app, based on blueprint, start it and wait for started
- local_action:
    module: ravello_app
    username: user@ravello.com
    password: password
    name: 'my-application-name'
    description: 'app desc'
    blueprint_id: '2452'
    wait: True
    wait_timeout: 600
    state: present
# Create app, based on blueprint
- local_action:
    module: ravello_app
    username: user@ravello.com
    password: password
    name: 'my-application-name'
    description: 'app desc'
    publish_optimization: performance
    cloud:AMAZON
    region: Oregon
    state: present
# List application example
- local_action:
    module: ravello_app
    name: 'my-application-name'
    service_name: 'ssh'
    state: list
# Delete application example
- local_action:
    module: ravello_app
    name: 'my-application-name'
    state: absent
# Create blueprint from existing app
- local_action:
    module: ravello_app
    name: 'my-application-name'
    blueprint_name: 'my-application-bp'
    blueprint_description: 'Blueprint of app xyz'
    state: blueprint
# Create blueprint based on app_template.yml
- local_action:
    module: ravello_app
    name: 'my-new-baseline'
    description: 'My new baseline'
    app_template: 'app_template.yml'
    state: design
  register: design_results
'''

import os
import base64
import getpass
import logging
import logging.handlers

##### Ravello API Wrappers #####
def set_cost_bucket(appID, appType, cost_bucket_name, client):
    available_cbs = [] 
    cost_buckets =  client.get_cost_buckets(permissions='execute')
    for cost_bucket in cost_buckets:
        available_cbs.append(cost_bucket['name'])
        if cost_bucket['name'] == cost_bucket_name:
            client.associate_resource_to_cost_bucket(
                         cost_bucket['id'], 
                         {'resourceId': appID, 'resourceType': appType}) 
            return
    if (cost_bucket_name == "Default") and (len(cost_buckets) >= 1):
        client.associate_resource_to_cost_bucket(
            cost_buckets[0]['id'], 
            {'resourceId': appID, 'resourceType': appType}) 
        return
    raise Exception("Cost Bucket: " + cost_bucket_name + " - not found.  Available cost buckets: " + ', '.join(available_cbs))
    return

def get_credentials():
        with open(os.path.expanduser("~/.ravello_login"),"r") as pf:
                username = pf.readline().strip()
                encrypted_password = pf.readline().strip()
        password = base64.b64decode(encrypted_password).decode()
        return username,password

def get_user_credentials(username):
        password = None
        if username:
                password = getpass.getpass('Enter a Password: ')
        else:
                #read user credentials from .ravello_login file in user HOMEDIR
                username,password = get_credentials()
        if not username or not password:
                log.error('User credentials are not set')
                print('Error: User credentials are not set')
                return None,None
        return username,password

def initlog(log_file):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logpath=os.path.join(os.getcwd(),log_file)
        handler = logging.handlers.RotatingFileHandler(logpath, maxBytes=1048576, backupCount=10)
        fmt = '%(asctime)s: %(filename)-20s %(levelname)-8s %(message)s'
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

def connect(username, password):
        client = RavelloClient()
        try:
                client.login(username, password)
        except Exception as e:
                sys.stderr.write('Error: {!s}\n'.format(e))
                log.error('Invalid user credentials, username {0}'.format(username))
                print('Error: Invalid user credentials, username {0}'.format(username))
                return None
        return client

def get_app_id(app_name,client):
        app_id=0
        for app in client.get_applications():
                if app['app_name'].lower() == app_name.lower():
                        app_id = app['id']
                        break
        if app_id == 0:
          module.fail_json(msg = 'ERROR: Cloud not find app: %s' % app_name)
        return app_id

def get_blueprint_id(blueprint_name,client):
        blueprint_id=0
        for blueprint in client.get_blueprints():
                if blueprint['name'].lower() == blueprint_name.lower():
                        blueprint_id = blueprint['id']
                        break
        if blueprint_id == 0:
          module.fail_json(msg = 'ERROR: Cloud not find blueprint: %s' % blueprint_name)
        return blueprint_id

def get_image_id(image_name,client):
        image_id=0
        for image in client.get_images():
                if image['name'].lower() == image_name.lower():
                        image_id = image['id']
                        break
        if image_id == 0:
          module.fail_json(msg = 'ERROR: Cloud not find VM image named: %s' % image_name)
        return image_id

def get_image(image_id,client):
        try:
          image = client.get_image(image_id)
        except Exception as e:
          module.fail_json(msg = 'ERROR: Cloud not find VM image id: %s' % image_id)
        return image

def main():
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.DEBUG)
    ### Optionally add a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    ### Add the console handler to the logger
    logger.addHandler(ch)    
    argument_spec=dict(
            # for nested babu only
            url=dict(required=False, type='str'),
            state=dict(default='present', choices=['design', 'present', 'started', 'absent', 'stopped', 'list', 'test', 'blueprint','blueprint_delete','blueprint_location']),
            username=dict(required=False, type='str'),
            password=dict(required=False, type='str'),
            name=dict(required=False, type='str'),
            app_name=dict(required=False, type='str'),
            description=dict(required=False, type='str'),
            blueprint_id=dict(required=False, type='str'),
            app_template=dict(required=False, default=None, type='path'),
            cloud=dict(required=False, type='str'),
            region=dict(required=False, type='str'),
            publish_optimization=dict(default='cost', choices=['cost', 'performance']),
            application_ttl=dict(default='-1', type='int'),
            service_name=dict(default='ssh', type='str'),
            blueprint_description=dict(required=False, type='str'),
            blueprint_name=dict(required=False, type='str'),
            wait=dict(type='bool', default=True ,choices=BOOLEANS),
            wait_timeout=dict(default=1200, type='int'),
            cost_bucket=dict(default='Organization', type='str')
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[['blueprint', 'app_template']],
        # We really really should support this...
        # supports_check_mode = True
    )
    module_fail.attach_ansible_modle(module)
    if not HAS_RAVELLO_SDK:
      module.fail_json(msg='ravello_sdk required for this module')
    # Get User credentials from Ansible (not too secure) or ENV variables (a little more secure)
    username = module.params.get('username', os.environ.get('RAVELLO_USERNAME', None)) 
    password = module.params.get('password', os.environ.get('RAVELLO_PASSWORD', None))
    if username and password:
      try:
        client = RavelloClient(username, password, module.params.get('url'))
      except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = 'ERROR: Failed to authenticate to Ravello using ansiblie provided credentials %s' % e,stdout='%s' % log_contents)
    else:
      #Get user credentials from SDK auth cache file (better)
      try:
        username, password  = get_user_credentials(None)
      except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = 'ERROR: Failed to retrieve credentials from Ravello SDK credentials cache %s' % e,stdout='%s' % log_contents)
      if not username or not password:
        module.fail_json(msg = 'ERROR: Unable to get any Ravello credentials!')
      try:
        client = connect(username, password)
      except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = 'ERROR: Failed to authenticate to Ravello using Ravello SDK credentials cache %s' % e,stdout='%s' % log_contents)
    state_arg = module.params.get('state')
    if state_arg == 'design':
      create_blueprint_from_template(client, module)
    elif state_arg == 'present':
      create_app_and_publish(client, module)
    elif state_arg == 'absent':
      action_on_app(module, client, 
              client.delete_application, 
              lambda: None, 'Deleted')
    elif state_arg == 'started':
      action_on_app(module, client, 
              client.start_application, 
              functools.partial(_wait_for_state,
                  client,'STARTED',module), 'Started')
    elif state_arg == 'stopped':
      action_on_app(module, client, 
              client.stop_application, 
              functools.partial(_wait_for_state,
                  client,'STOPPED',module), 'Stopped')
    elif state_arg == 'list':
      list_app(client, module)
    elif state_arg == 'blueprint':
      create_blueprint_from_existing_app(module, 
              client, client.create_blueprint)
    elif state_arg == 'blueprint_delete':
      action_on_blueprint(module, client, 
              client.delete_blueprint)
    elif state_arg == 'blueprint_location':
      action_on_blueprint(module, client, 
              client.get_blueprint_publish_locations)
    elif state_arg == 'test':
      module.exit_json(msg = 'Authentication to Ravello successful')

def _wait_for_state(client, state, module):
    if module.params.get('wait') == False:
        return
    wait_timeout = module.params.get('wait_timeout')
    app_id = 0
    wait_till = time.time() + wait_timeout
    while wait_till > time.time():
        if app_id > 0:
            app = client.get_application(app_id)
        else:
            app =  client.get_application_by_name(module.params.get('app_name'))
            app_id = app['id']
        states = list(set((vm['state'] \
                for vm in app.get('deployment', {}).get('vms', []))))
        if "ERROR" in states:
            log_contents = log_capture_string.getvalue()
            log_capture_string.close()
            module.fail_json(msg = 'Vm got ERROR state',stdout='%s' % log_contents)
        if len(states) == 1 and states[0] == state:
            return
        time.sleep(10)
    log_contents = log_capture_string.getvalue()
    log_capture_string.close()
    module.fail_json(msg = 'Timed out waiting for async operation to complete.',  
            stdout='%s' % log_contents)

def is_wait_for_external_service(supplied_service,module):
    return supplied_service['name'].lower() == \
            module.params.get('service_name').lower() and \
            supplied_service['external'] == True

def get_list_app_vm_result(app, vm, module):
    for supplied_service in vm['suppliedServices']:            
    	if is_wait_for_external_service(supplied_service, module):
            for network_connection in vm['networkConnections']:
                if network_connection['ipConfig']['id'] == \
                        supplied_service['ipConfigLuid']:
                    dest = network_connection['ipConfig'].get('fqdn')
                    port = int(supplied_service['externalPort'].split(",")[0].split("-")[0])
                    return (dest,port)
	            
def list_app(client, module):
    try:
        app_name = module.params.get("app_name")
        app = client.get_application_by_name(app_name)
        results = []
        for vm in app['deployment']['vms']:
            if vm['state'] != "STARTED":
                continue
            (dest,port) = get_list_app_vm_result(app, vm, module)
            results.append({'host': dest, 'port': port})
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.exit_json(changed=True, app_name='%s' % app_name, 
                results='%s' % results,stdout='%s' % log_contents)
    except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = '%s' % e,stdout='%s' % log_contents)

def action_on_app(module, client, runner_func, waiter_func, action):
    try:
        app_name = module.params.get("app_name")
        app = client.get_application_by_name(app_name)
        runner_func(app['id'])
        waiter_func()
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.exit_json(changed=True, 
                app_name='%s application: %s' %(action, app_name),
                stdout='%s' % log_contents)
    except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = '%s' % e,stdout='%s' % log_contents)

def create_blueprint_from_existing_app(module, client, runner_func):
    app_name = module.params.get("app_name")
    app = client.get_application_by_name(app_name)
    blueprint_name = module.params.get("blueprint_name")
    blueprint_description = module.params.get("blueprint_description")
    blueprint_dict = {"applicationId":app['id'], 
            "blueprintName":blueprint_name, "offline": True,  
            "description":blueprint_description }
    try:
        blueprint_id=((runner_func(blueprint_dict))['_href'].split('/'))[2]
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.exit_json(changed=True, 
                app_name='%s' % app_name, 
                blueprint_name='%s' % blueprint_name, 
                blueprint_id='%s' % blueprint_id)
    except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = '%s' % e,stdout='%s' % log_contents)        

def action_on_blueprint(module, client, runner_func):
    if module.params.get("blueprint_id"):
      blueprint_id = module.params.get("blueprint_id")
    elif module.params.get("blueprint_name"):
      blueprint_name = module.params.get("blueprint_name")
      blueprint_id = get_blueprint_id(blueprint_name, client)
    try:
        output = runner_func(blueprint_id)
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.exit_json(changed=True, stdout='%s' % log_contents, 
                blueprint_id='%s' % blueprint_id, output='%s' % output)
    except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = '%s' % e,stdout='%s' % log_contents)        


def create_blueprint_from_template(client, module):
    app_name = module.params.get("app_name")
    # Assert app does not exist in ravello
    cap = client.get_applications({'name': app_name})
    if cap:
      module.fail_json(msg='ERROR: Application %s already exists!' % \
              app_name, changed=False)
    # Assert blueprint does not exist in ravello
    blueprint_name = app_name + "-bp"
    bp = client.get_blueprints({'name': blueprint_name})
    if bp:
      module.fail_json(msg='ERROR: Blueprint %s already exists!' % \
              blueprint_name, changed=False)
    app_description = module.params.get("description")
    # Open local app template
    if not module.params.get("app_template"):
        module.fail_json(msg='Must supply an app_template for design state.', \
                changed=False)
    app_template = module.params.get("app_template")
    with open(app_template, 'r') as data:
      try:
        read_app = yaml.load(data)
      except yaml.YAMLError as exc:
        print(exc)
    app_request = {}
    # Create random name extension token for app
    rand_str = lambda n: ''.join([random.choice(string.lowercase) for i in xrange(n)])
    app_request['name'] = "tmp-app-build-" + rand_str(10)
    if client.get_applications({'name': app_request ['name'] }):
      module.fail_json(msg='ERROR: Temporary application build %s already exists!' % \
              app_name, changed=False)
    # initialize app
    ravello_template_set(app_request, 'description', app_description)
    ravello_template_set(app_request, 'design.vms', [])
    # Check template is valid
    for vm in read_app['vms']:
      assert_vm_valid(client, module, vm)
      app_request['design']['vms'].append(vm)
    # Create the tmp-app in ravello
    try:
        created_app = client.create_application(app_request)
    except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = '%s' % e,stdout='%s' % log_contents, 
                jsonout='%s' % app_request)
    appID = created_app['id']
    blueprint_dict = {
            "applicationId":appID, 
            "blueprintName":blueprint_name, 
            "offline": False, 
            "description":app_description 
            }
    # Generate subnets if they are defined in the template
    # Otherwise generate subnets compatible with defined VM IPs 
    delete_autogenerated_subnet(client, module, appID)
    if check_for_param(read_app, 'network.subnets', required=False):
        netlist = []
        for subnet in read_app['network']['subnets']:
            netlist.append(IPNetwork(subnet))
        netlist = sorted(netlist)
        for i in range(len(netlist) - 1):
            if (not IPSet(netlist[i]).isdisjoint(IPSet(netlist[i + 1]))):
                raise Exception('Overlapping Subnets')
            else:
                create_subnet_with_ip_pool(client, module, appID, netlist[i])
        create_subnet_with_ip_pool(client, module, appID, netlist[len(netlist) - 1])
    else:
        detect_ips_and_and_create_compatible_subnets(client, module, appID, app_request)
    # Get the ravello-assigned internal luids to fix assigned IPs and services
    update_app_with_internal_luids(client, module, app_request, appID)
    try:
    # create bp from tmp-app and delete tmp-app
        blueprint_id= \
          ((client.create_blueprint(blueprint_dict))['_href'].split('/'))[2]
        client.delete_application(appID)
        module.exit_json(changed=True, app_name='%s' % app_name, 
                blueprint_name='%s' % blueprint_name, 
                blueprint_id='%s' % blueprint_id)
    except Exception, e:
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()
        module.fail_json(msg = '%s' % e,stdout='%s' % log_contents)

def create_app_and_publish(client, module):
    #validation
    if not module.params.get("blueprint_id"):
            module.fail_json(msg='Must supply a blueprint_id', changed=False)
    if 'performance' == module.params.get("publish_optimization"):
        if not module.params.get("cloud"):
            module.fail_json(msg=\
                    'Must supply a cloud when publish optimization is performance', 
                    changed=False)
        if not module.params.get("region"):
            module.fail_json(msg=\
                    'Must supply a region when publish optimization is performance', 
                    changed=False)
    app = {
            'name': module.params.get("app_name"), 
            'description': module.params.get("description",''), 
            'baseBlueprintId': module.params.get("blueprint_id")
            }    
    app = client.create_application(app)
    req = {}
    if 'performance' == module.params.get("publish_optimization"):
        req = {
                'id': app['id'], 
                'preferredRegion': module.params.get("region"), 
                'optimizationLevel': 'PERFORMANCE_OPTIMIZED'
                }
    ttl=module.params.get("application_ttl")
    if ttl != -1:
        ttl =ttl * 60
        exp_req = {'expirationFromNowSeconds': ttl}
        client.set_application_expiration(app,exp_req)
    client.publish_application(app, req)
    set_cost_bucket(app['id'], 'application', 
            module.params.get('cost_bucket'), client)
    get_vm_hostnames(app['id'], client, module)
    _wait_for_state(client,'STARTED',module)
    log_contents = log_capture_string.getvalue()
    log_capture_string.close()
    module.exit_json(changed=True, 
            app_name='%s' % module.params.get("app_name"),
            stdout='%s' % log_contents, 
            app_id='%s' % app['id'])

def get_vm_hostnames(app_id, client, module):
    published_app = client.get_application(app_id, aspect='deployment')
    vm_hostname_dict = {}
    for vm in ravello_template_get(published_app, 'deployment.vms'):
       if len(vm['hostnames']) < 1:
           module.fail_json(msg="Could not obtain vm hostname list from app." +  
                                 "VMs must contain at least one internal hostname.")
       hostname = vm['hostnames'][0] 
       vm_hostname_dict[hostname] = {}
       vm_hostname_dict[hostname]['internal'] = vm['hostnames']
       vm_hostname_dict[hostname]['external'] = vm['externalFqdn']

# import module snippets
import ansible
import os
import functools
import logging
import io
import datetime
import sys
import yaml
import json
import re

from netaddr import *

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
log_capture_string = io.BytesIO()

from ansible.module_utils.basic import *

##### Template Error Checking Definitions #####

def assert_hd_valid(client, module, hd):
    check_for_param(hd, 'index')
    check_for_param(hd, 'type', valid=['DISK','CDROM'], 
            default_if_missing='DISK')
    check_for_param(hd, 'controller', valid=['virtio', 'ide'],
            default_if_missing='virtio')
    check_for_param(hd, 'controller', valid=['virtio', 'ide'],
            default_if_missing='virtio')
    check_for_param(hd, 'boot', valid=[True, False], 
            default_if_missing='False')
    check_for_param(hd, 'name',
            default_if_missing=('Disk' + hd['name']))
    check_for_param(hd, 'size.unit', valid=['GB', 'MB'],
            default_if_missing='GB')
    check_for_param(hd, 'size.value', 
            valid=(lambda n: ((n is int) and (n > 0))))
    assert_hd_image_exists_in_ravello(client, module, hd)
    return hd

def assert_hd_image_exists_in_ravello(client, module, hd):
    # Check image name or ID exists in ravello
    if 'baseDiskImageId' in hd:
      image = get_diskimage(client, hd['baseDiskImageId'])
      if image is None:
        module.fail_json(msg=\
                'FATAL ERROR nonexistent baseDiskImageId %s specified!' 
            % hd['baseDiskImageId'])
    elif 'imageName' in hd:
      image = get_diskimage(client, hd['imageName'])
      if image is None:
        module.fail_json(msg=\
                'FATAL ERROR nonexistent imageName %s specified!' 
           % hd['imageName'])
    if 'baseDiskImageId' in hd or 'imageName' in hd:
      if hd['size']['value'] < image['size']['value']:
        module.fail_json(msg=\
                'ERROR HD size value (%s) is smaller than the image (%s)' 
          % (hd['size']['value'], image['size']['value']))
      else:
        hd['baseDiskImageId'] = image['id']

def assert_nic_valid(client, module, nic):
    check_for_param(nic, 'ipConfig')
    check_for_param(nic, 'device.index')
    check_for_param(nic, 'device.name', 
            default_if_missing=('nic', nic['device']['index']))
    check_for_param(nic, 'device.deviceType', valid=['virtio', 'e1000'],
            default_if_missing='virtio')
    check_for_param(nic, 'device.useAutomaticMac', valid=[True, False], 
            default_if_missing=True)
    if not nic['device']['useAutomaticMac']:
        check_for_param(nic, 'device.mac',
          fail_msg='ERROR useAutomaticMac set to False but ' + \
                   'no static mac set for VM %s NIC index')
    auto_ip = check_for_param(nic, 
            'ipConfig.autoIpConfig',
            required=False)
    static_ip = check_for_param(nic, 
            'ipConfig.staticIpConfig', required=False)
    if static_ip:
        check_for_param(nic, 'ipConfig.staticIpConfig.ip')
        check_for_param(nic, 'ipConfig.staticIpConfig.mask')    
    if (auto_ip == static_ip):
        module.fail_json(msg=\
                'Error: exactly one of [autoIpConfig,staticIpConfig] required')

def assert_vm_valid(client, module, vm):
    #* Set vm description if undef'd
    if not 'description' in vm:
      vm['description'] = ""
    # Check Template Valid
    check_for_param(vm, 'description',
            default_if_missing="")
    check_for_param(vm, 'numCpus')
    check_for_param(vm, 'memorySize.value')
    check_for_param(vm, 'memorySize.unit', 
            default_if_missing='GB')
    check_for_param(vm, 'supportsCloudInit', 
            fail_msg='Error: Template must support cloudInit')
    check_for_param(vm, 'keypairId')
    check_for_param(vm, 'keypairName')
    check_for_param(vm, 'userData')
    check_for_param(vm, 'stopTimeout',
            default_if_missing=300)
    check_for_param(vm, 'bootOrder', 
            default_if_missing=['DISK', 'CDROM'])
    check_for_param(vm, 'hardDrives')
    check_for_param(vm, 'networkConnections')
    check_for_param(vm, 'networkConnections')
    # Set vm tag if def'd
    if 'tag' in vm:
      vm['description'] = vm['description'] + "\ntag:" + vm['tag'] + "\n"
    # Set new_vm params
    ravello_template_set(vm, 'baseVmId', 0)
    ravello_template_set(vm, 'os', 'linux_manuel')
    #* set hard drives
    for hd in vm['hardDrives']:
        hd = assert_hd_valid(client, module, hd)
    #* set nics
    for nic in vm['networkConnections']:
        assert_nic_valid(client, module, nic)
    if 'suppliedServices' in vm:
      for svc in vm['suppliedServices']:
        check_for_param(svc, 'name')
        #check_for_param(svc, 'ip')
        check_for_param(svc, 'portRange')
    # add vm to app
    return vm

def create_subnet_with_ip_pool(client, module, appID, netip):
    # create the vlan
    created_app = client.get_application(appID)
    check_for_param(created_app, 'design.network.switches', 
            default_if_missing=[])
    new_switch_path = path_for_next_item(created_app, 'design.network.switches')
    ravello_template_set(created_app, 
            new_switch_path + '.networkSegments.0.vlanId', 1)
    client.update_application(created_app)
    created_app = client.get_application(appID)
    check_for_param(created_app, 'design.network.subnets', 
            default_if_missing=[])
    new_subnet_path = path_for_next_item(created_app, 'design.network.subnets')
    ravello_template_set(created_app, new_subnet_path + '.ipVersion', 'IPV4')
    ravello_template_set(created_app, new_subnet_path + '.mask', str(netip.netmask))
    ravello_template_set(created_app, new_subnet_path + '.net', str(netip[0]))
    new_switch_network_segment_id = \
            ravello_template_get(created_app, 
                new_switch_path + '.networkSegments.0.id')
    ravello_template_set(created_app, 
            new_subnet_path + '.networkSegmentId', 
            new_switch_network_segment_id)
    client.update_application(created_app)
    created_app = client.get_application(appID)
    check_for_param(created_app, 'design.network.services.networkInterfaces', 
            default_if_missing=[])
    new_l3_nic_path = path_for_next_item(created_app,
            'design.network.services.networkInterfaces')
    ravello_template_set(created_app, 
          new_l3_nic_path + \
            '.ipConfigurations.0.staticIpConfig', 
          {
            'ip': str(netip[1]),
            'mask': str(netip.netmask)
          })
    ravello_template_set(created_app, 
          new_l3_nic_path + \
            '.ipConfigurations.1.staticIpConfig', 
          {
            'ip': str(netip[2]),
            'mask': str(netip.netmask)
          })
    client.update_application(created_app)
    created_app = client.get_application(appID)
    check_for_param(created_app, 
            'design.network.services.routers.0.ipConfigurationIds',
            default_if_missing=[])
    router_ip_config_ids = ravello_template_get(created_app,
            'design.network.services.routers.0.ipConfigurationIds')
    router_ip_config_ids.append(ravello_template_get(created_app,
                new_l3_nic_path + '.ipConfigurations.1.id'))
    if 'ports' not in ravello_template_get(created_app, new_switch_path):
        ravello_template_set(created_app, new_switch_path + '.ports', [])
    create_port_on_switch(created_app, new_switch_path,
            ravello_template_get(created_app,
                new_l3_nic_path + '.id'),
            'SERVICES')
    client.update_application(created_app)
    created_app = client.get_application(appID)
    check_for_param(created_app, 'design.network.services.dhcpServers', 
            default_if_missing=[])
    new_dhcp_path = path_for_next_item(created_app,
            'design.network.services.dhcpServers')
    ravello_template_set(created_app, new_dhcp_path + '.mask', str(netip.netmask))
    ravello_template_set(created_app, new_dhcp_path + '.poolStart', str(netip[0]))
    ravello_template_set(created_app, new_dhcp_path + '.poolEnd', str(netip[-1]))
    ravello_template_set(created_app, new_dhcp_path + '.ipConfigurationId', 
            ravello_template_get(created_app, new_l3_nic_path + '.ipConfigurations.0.id'))
    ravello_template_set(created_app, new_dhcp_path + '.gatewayIpConfigurationId', 
            ravello_template_get(created_app, new_l3_nic_path + '.ipConfigurations.1.id'))
    check_for_param(created_app, 
            'design.network.services.dnsServers.0.ipConfigurationIds',
            default_if_missing=[])
    dns_ip_config_ids = ravello_template_get(created_app,
            'design.network.services.dnsServers.0.ipConfigurationIds')
    dns_ip_config_ids.append(ravello_template_get(created_app, 
        new_l3_nic_path + '.ipConfigurations.0.id'))
    ravello_template_set(created_app, new_dhcp_path + '.dnsIpConfigurationId', 
            ravello_template_get(created_app, new_l3_nic_path + '.ipConfigurations.0.id'))
    client.update_application(created_app)

def delete_autogenerated_subnet(client, module, appID):
    created_app = client.get_application(appID)
    ravello_template_set(created_app, 'design.network.switches', [])
    ravello_template_set(created_app, 'design.network.subnets', [])
    ravello_template_set(created_app, 'design.network.services.networkInterfaces', [])
    ravello_template_set(created_app, 'design.network.services.dhcpServers', [])
    client.update_application(created_app)

def create_port_on_switch(created_app, switch_path, device_id, device_type):
    port_path = path_for_next_item(created_app,
            switch_path + '.ports')
    #ravello_template_set(created_app, port_path, {})
    ravello_template_set(created_app,
            port_path + '.deviceId',
            device_id)
    ravello_template_set(created_app,
            port_path + '.deviceType',
            device_type)
    ravello_template_set(created_app,
            port_path + '.index',
            int(port_path.split('.')[-1]) + 1)
    ravello_template_set(created_app,
            port_path + '.networkSegmentReferences.0.networkSegmentId',
            ravello_template_get(created_app,
                switch_path + '.networkSegments.0.id'))
    ravello_template_set(created_app,
            port_path + '.networkSegmentReferences.0.anyNetworksegment',
            False)
    ravello_template_set(created_app,
            port_path + '.networkSegmentReferences.0.egressPolicy',
            'UNTAGGED')
    return

def path_for_next_item(app_json, jspath):
    return jspath + '.' + str(len(ravello_template_get(app_json, jspath)))

def path_from_ip(created_app, path_map, ip_addr):
    for net_block, path in path_map.iteritems():
       if IPAddress(ip_addr) in IPNetwork(net_block):
           return path 
    raise Exception('no subnet for ip: ' + ip_addr + '...' + json.dumps(path_map))

def create_dhcp_ip_map(created_app):
    dhcp_servers = ravello_template_get(created_app,
            'design.network.services.dhcpServers')
    ip_index_map = {}
    for i, dhcp in enumerate(dhcp_servers):
        cidr_num = IPAddress(dhcp['mask']).netmask_bits()
        net_block = dhcp['poolStart'] + '/' + str(cidr_num)
        ip_index_map[net_block] =  \
                'design.network.services.dhcpServers.' + str(i)
    return ip_index_map

def create_subnet_ip_map(created_app):
    subnets = ravello_template_get(created_app,
            'design.network.subnets')
    ip_index_map = {}
    for i, subnet in enumerate(subnets):
        cidr_num = IPAddress(subnet['mask']).netmask_bits()
        net_block = subnet['net'] + '/' + str(cidr_num)
        ip_index_map[net_block] =  \
                'design.network.subnets.' + str(i)
    return ip_index_map

def switch_path_from_ip(created_app, subnet_ip_map, ip_addr):
    network_segment_id = ravello_template_get(created_app,
        path_from_ip(created_app, subnet_ip_map, ip_addr) + '.networkSegmentId')
    switches = ravello_template_get(created_app,
        'design.network.switches')
    for i, switch in enumerate(switches):
        if switch['networkSegments'][0]['id'] == network_segment_id:
          return 'design.network.switches.' + str(i)
    raise Exception('Invalid network segment')


def json_path_list_append(json_item, jspath, value):
    item_list = ravello_template_get(json_item, jspath)
    item_list.append(value)

def update_app_with_internal_luids(client, module, app_request, appID):
    # update vms with ravello auto-gen'd luids
    created_app = client.get_application(appID)
    reserved_entries = []
    hostname_ip_mapping = {}
    dhcp_ip_mapping = create_dhcp_ip_map(created_app)
    original_subnet_config_ids = ravello_template_get(created_app,
            'design.network.subnets.0.ipConfigurationIds')
    original_switch_ports = ravello_template_get(created_app,
            'design.network.switches.0.ports')
    subnet_ip_mapping = create_subnet_ip_map(created_app)
    for dhcp in created_app['design']['network']['services']['dhcpServers']:
        if 'reservedIpEntries' not in dhcp:
            dhcp['reservedIpEntries'] = []
    for vm in app_request['design']['vms']:
        hostname = vm['hostnames'][0]
        hostname_ip_mapping[hostname] = {}
        for nic in vm['networkConnections']:
            if check_for_param(nic, 'ipConfig.autoIpConfig.reservedIp',
                    required=False):
                hostname_ip_mapping[hostname][nic['name']] = \
                      {'ip': nic['ipConfig']['autoIpConfig']['reservedIp'],
                       'dhcpReservedIp': True}
            elif check_for_param(nic, 'ipConfig.staticIpConfig.ip',
                    required=False):
                hostname_ip_mapping[hostname][nic['name']] = \
                      {'ip': nic['ipConfig']['staticIpConfig']['ip'],
                       'dhcpReservedIp': False}
            else:
                hostname_ip_mapping[hostname][nic['name']] = {'dhcpReservedIp': False}
    for i, vm in enumerate(created_app['design']['vms']):
        for nic in vm['networkConnections']:
          nic_ipconf_id = nic['ipConfig']['id']
          nic_id = nic['id']
          nic_name = nic['name']
          vm_hostname = vm['hostnames'][0]
          hostname_ip_mapping[vm_hostname][nic_name]['ipconf_id'] = nic_ipconf_id
          if nic_name in hostname_ip_mapping[vm_hostname]:
              nic_ip = hostname_ip_mapping[vm_hostname][nic_name]['ip']
              if hostname_ip_mapping[vm_hostname][nic_name]['dhcpReservedIp']:
                  item = {
                         'ipConfigurationId': nic_ipconf_id,
                          'ip': nic_ip
                         }
                  json_path_list_append(created_app,
                          path_from_ip(created_app, 
                              dhcp_ip_mapping,
                              nic_ip) + '.reservedIpEntries',
                          item)
              switch_path = switch_path_from_ip(created_app, 
                      subnet_ip_mapping,
                      nic_ip) 
              subnet_ipconfig_path = path_from_ip(created_app, 
                      subnet_ip_mapping,
                      nic_ip)
          else:
              switch_path = 'design.network.switches.0'
              subnet_ipconfig_path = 'design.network.subnets.0'
          json_path_list_append(created_app,
                  subnet_ipconfig_path + '.ipConfigurationIds',
                  nic_ipconf_id)
          create_port_on_switch(created_app, 
                  switch_path,
                  nic_id,
                  'VM')
        if 'suppliedServices' in vm:
            for j, svc in enumerate(vm ['suppliedServices']):
                old_vm = filter(lambda v: v['hostnames'] == vm['hostnames'], 
                                 app_request['design']['vms'])[0]
                if check_for_param(old_vm, 'suppliedServices.' + str(j), required=False):
                    service_req = ravello_template_get(old_vm['suppliedServices'], str(j))
                    nic_name = ""
                    if 'device' in service_req:
                        nic_name = service_req['device']
                    else: 
                         found = False
                         for entry in hostname_ip_mapping[vm_hostname]:
                             if service_req['ip'] == hostname_ip_mapping[vm_hostname][entry]['ip']:
                                 found = True
                                 nic_name = entry
                                 break
                         if not found:
                             module_fail("ip not found: " + service_req['ip'] + "for " + vm_hostname + " " + nic_name + "                      " + json.dumps(hostname_ip_mapping))
                if (nic_name not in hostname_ip_mapping[vm_hostname]):
                    module_fail(nic_name + vm_hostname + "\n" + json.dumps(hostname_ip_mapping))
                svc['useLuidForIpConfig'] = True
                svc['ipConfigLuid'] = \
                    hostname_ip_mapping[vm_hostname][nic_name]['ipconf_id']
    client.update_application(created_app)

def detect_ips_and_and_create_compatible_subnets(client, module, appID, app_request):
    net_list = []
    for vm in app_request['design']['vms']:
        for nic in vm['networkConnections']:
            if check_for_param(nic, 'ipConfig.autoIpConfig.reservedIp', required=False):
                ip = nic['ipConfig']['autoIpConfig']['reservedIp']
                subnet_exists = False
                for net in net_list:
                   if ip in net:
                       subnet_exists = True
                if not subnet_exists:
                    new_net = IPNetwork(ip + '/16')
                    net_list.append(new_net)
            elif check_for_param(nic, 'ipConfig.staticIpConfig.ip', required=False):
                    '.'.join(nic['ipConfig']['staticIpConfig']['ip'].split('.')[:-3])
    # Remove the Ravello auto-generated subnet
    if len(net_list) == 0:
        create_subnet_with_ip_pool(client, module, appID, IPNetwork('192.168.0.0/16'))
    else:
        for net in net_list:
            create_subnet_with_ip_pool(client, module, appID, net)

##### Application Json Tools #####

#def maybe_digit(item):
#    if (item.isdigit()):
#      return int(item)
#    else:
#      return item
#
#def json_insert_head(json_slice, key, value):
#    if type(key) is int:
#        if len(json_slice) <= key:
#          json_slice.insert(key, value)
#        else:
#            json_slice[key] = value
#    else:
#        json_slice[key] = value
#    return json_slice
#
#def ravello_template_set(json_slice, jspath_str, value):
#    jspath = re.split(r'(?<!\\)\.', jspath_str)
#    def recur (json_slice, jspath, value):
#        if len(jspath) > 1:
#            if not json_head_contains(json_slice, maybe_digit(jspath[0])):
#                if jspath[1].isdigit():
#                    json_slice = json_insert_head(json_slice, maybe_digit(jspath[0]), [])
#                else:
#                    json_slice = json_insert_head(json_slice, maybe_digit(jspath[0]), {})
#            json_insert_head(json_slice, maybe_digit(jspath[0]),
#                        recur(json_slice[maybe_digit(jspath[0])], 
#                            jspath[1:], value))
#        elif len(jspath) == 1:
#            json_slice = json_insert_head(json_slice, maybe_digit(jspath[0]), value)
#        else:
#            raise Exception("Error: invalid json path string: " + jspath_str)
#        return json_slice
#    return recur(json_slice, jspath, value)
#
## return kwargs[k] if it exists,
## otherwise return default
#def from_kwargs(kwargs, k, default):
#    if k in kwargs:
#        return kwargs[k]
#    elif type(default) is Exception:
#        raise default
#    else:
#      return default
#
#def json_head_contains(json_item, key):
#    if json_item is None:
#        return False
#    if type(key) is int:
#        if len(json_item) <= key:
#          return False
#        else:
#            return True
#    else:
#        return (key in json_item)
#
#def ravello_template_get(json_item, jspath_str, **kwargs):
#    jspath = re.split(r'(?<!\\)\.', jspath_str)
#    def recur(json_slice, jspath):
#        if len(jspath) > 1:
#            if not json_head_contains(json_slice, maybe_digit(jspath[0])):
#                raise Exception("error: invalid json_path string: " + jspath_str)
#            return recur(json_slice[maybe_digit(jspath[0])], jspath[1:])
#        elif len(jspath) == 1:
#            if not json_head_contains(json_slice, maybe_digit(jspath[0])):
#                raise Exception("error: invalid json_path string: " + jspath_str)
#            else:
#                return json_slice[maybe_digit(jspath[0])]
#        else:
#            raise exception("error: invalid json_path string: " + jspath_str)
#    return recur(json_item, jspath)
#
#class ModuleFail:
#    def __init__(self):
#        self.module = None
#    def attach_ansible_modle(self, module):
#        self.module = module
#    def __call__(self, msg):
#        if (self.module == None):
#            raise Exception(msg)
#        else:
#            self.module.fail_json(msg=msg)
#
#def check_for_param(json_item, jspath, **kwargs):
#    full_jspath = jspath
#    def cfp_helper(json_item, jspath, **kwargs):
#         valid = from_kwargs(kwargs, 'valid_options', []) 
#         fail_msg = from_kwargs(kwargs, 'fail_msg',
#                 "Template Error: " + full_jspath + " - Missing or invalid.\nIn json item: "  + json.dumps(json_item))
#         required = from_kwargs(kwargs, 'required', True)
#         if type(valid) is str:
#             valid = [valid]
#         if type(valid) is list:
#             valid_list = valid
#             valid = lambda val: val in valid_list
#         if not callable(valid):
#             raise Exception('Error: `valid` kwarg must of type string, list, or parity 1 function')
#         def recur(json_slice, jspath):
#             if type(jspath) is str:
#               jspath = re.split(r'(?<!\\)\.', jspath)
#             if len(jspath) > 1:
#                 if not json_head_contains(json_slice, maybe_digit(jspath[0])):
#                     if not required:
#                         return False
#                     if 'default_if_missing' in kwargs:
#                         ravello_template_set(json_item, '.'.join(jspath), value)
#                     module_fail(fail_msg)
#                 return recur(json_slice[maybe_digit(jspath[0])], jspath[1:])
#             elif len(jspath) == 1:
#                 if not json_head_contains(json_slice, maybe_digit(jspath[0])):
#                     if not required:
#                         return False
#                     if 'default_if_missing' not in kwargs:
#                       module_fail(fail_msg)
#                     else:
#                       json_insert_head(json_slice, maybe_digit(jspath[0]),
#                               kwargs['default_if_missing'])
#                 if 'valid' not in kwargs:
#                     return True
#                 else:
#                     return valid(json_slice[maybe_digit(jspath[0])])
#             else:
#                 raise Exception("Error: invalid json path string")
#         return recur(json_item, jspath)
#    return cfp_helper(json_item, jspath, **kwargs)


main()
