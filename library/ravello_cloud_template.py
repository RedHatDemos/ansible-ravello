#!/bin/python

DOCUMENTATION='''
---
module: ravello_cloud_template
short_description: Quickly define cloud templates for ravellosystems applications
description:
    - This module provides defaults for most Ravello application parameters,
      allowing template specifications to be concise.  The module takes an
      ansible yaml dictionary of VM instances and network subnet definitions,
      and produces a complete cloud template which is ready to be used by the 
      ravello_module.  
    - VMs can be assigned public and private keys for the ravello dynamic inventory
      to use when setting up ssh connections and proxies
options:
    path:
      description:
        - output destination of template.
    instances:
      description:
        - a dictionary of virtual machine definitions. see examples for full usage.
    subnets:
      description:
        - a list of CIDR block strings.
'''


EXAMPLES='''
---
# Create a ravello template for an app with 
# the bastion as a proxy tunnel to reach the webserver
- ravello_cloud_template:
    path: "{{ template_in_path }}"
    subnets:
      - 10.0.0.0/24
    instances: 
      - name: bastion
        services:
          - protocol: ssh
            port: 22
        # This will install the public key to .ssh/authorized_keys
        public_key: {{ your_public_key }}
        # This tags the VM with the path of the ssh key on the
        # control node that ansible should use to connect.
        # It does not install the private key to the machine.
        private_key_path: {{ ansible_private_key_path }}
      - name: webserver
        public_key: {{ your_public_key }}
        private_key_file: {{ ansible_private_key_path }}
        # Tags the instance for the ravello dynamic inventory
        # to set up the bastion as a proxy tunnel for this machine
        proxy: bastion

# Create a customized application with two 
# webservers and a bastion.  
- ravello_cloud_template:
    path: "{{ template_in_path }}"
    subnets:
      - 192.168.0.0/16
    instances:
      - name: bastion
        hostname: bastion.example.com
        cpus: 1
        ram: 2
        disks:
          - size: 50
          - size: 100
        nics:
          - name: eth0
            ip: 192.168.1.10
        services:
            - protocol: ssh
              port: 22
        public_key: {{ your_public_key }}
        private_key_file: {{ ansible_private_key_path }}
      - name: webserver1
        hostname: webserver1.example.com
        proxy: bastion
        groups: 
          - webservers
        cpus: 2
        ram: 4
        disks:
          - size: 50
        nics:
          - name: eth0
            ip: 192.168.10.11
        services:
            - protocol: http
              port: 80
        public_key: {{ your_public_key }}
        private_key_file: {{ ansible_private_key_path }}
      - name: webserver2
        hostname: webserver2.example.com
        proxy: bastion
        groups: 
          - webservers 
        cpus: 2
        ram: 4
        disks:
          - size: 50
        nics:
          - name: eth0
            ip: 192.168.10.12
        services:
            - protocol: http
              port: 80
        public_key: {{ your_public_key }}
        private_key_file: {{ ansible_private_key_path }}

# Full api for the instances field.
# Required values are marked as <required>
# Otherwise, default values are shown
instances:
  - name: <required>
    public_key: <required>
    private_key_path: <required>
    description: None
    cpus: 1
    ram: 2
    mem_unit: GB
    # ravello keypair name
    keypair_name: None
    # ravello keypair id
    keypair_id: None
    # hostname can also be a list of hostnames
    hostname: <name>.example.com
    # <name> of instance to proxy through
    proxy: None
    # username and ansible remote_user
    remote_user: cloud_user
    # Nested Virtualization
    allow_nested: False
    # Enable Baremetal
    prefer_physical: False
    # Boot image must be present on account
    boot_image: rhel-guest-image-7.3-35.x86_64
    # hard drives
    disks:
      - name: vol
        size: 40
        mem_unit: GB
        bootable: <True on first hdd in list, False otherwise>
        image: <VM boot_image if bootable, none otherwise>
        device_type: DISK
        controller: virtio
    # network devices
    nics:
      - name: <required>
        controller: virtio
        ip: None (auto-assigned)
        public_ip: True
        mac: None (auto-assigned)
    # ports to open
    services:
     - protocol: <required>
       name: <protocol>
       # network device
       device: None (auto-assigned)
       # port or range of ports
       port: <required>
    # ansible inventory groups to add the instance to 
    groups: [<name>]
    # ansible variables to set when inventoried
    ansible_vars: {}
'''
    

import sys
import yaml
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

import os
import base64
import getpass
import logging
import logging.handlers
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
        

from ansible.module_utils.ravello_utils import *
from ansible.module_utils.basic import *
#from ansible.module_utils.facts import *

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
log_capture_string = io.BytesIO()

## Classes to organize VM defaults
## and handle yaml formatting
class HardDrive:
    def __init__(self, **kwargs):
        self.index  = from_kwargs(kwargs, 'index', Exception("index required for hdds"))
        self.name  = from_kwargs(kwargs, 'name', 'vol' + str(self.index))
        self.memory_size = from_kwargs(kwargs, 'size', 40)
        self.memory_unit = from_kwargs(kwargs, 'mem_unit', "GB")
        self.bootable = from_kwargs (kwargs, 'bootable', False)
        self.controller = from_kwargs(kwargs, 'controller', 'virtio')
        self.image =  from_kwargs(kwargs, 'image', '')
        self.device_type = from_kwargs(kwargs, 'device_type', "DISK")
    def to_yaml_dict(self, index):
        hd_yaml = {
            'index': self.index,
            'boot': self.bootable,
            'controller': self.controller,
            'name': self.name,
            'size' : {
                'unit': self.memory_unit,
                'value': self.memory_size
              },
            'type': self.device_type
          }
        if self.image != '':
            hd_yaml['imageName'] = self.image
        return hd_yaml

class Service:
    def __init__(self, **kwargs):
        self.external = from_kwargs(kwargs, 'external', True)
        self.port_range = \
          from_kwargs(kwargs, 
                     'port', Exception('Missing required field: port'))
        self.protocol = \
            from_kwargs(
                kwargs, 
                'protocol', Exception('Missing required field: protocol'))
        self.device = \
            from_kwargs(kwargs, 'device', None)
        self.name = \
            from_kwargs(kwargs, 'name', self.protocol.lower())
    def to_yaml_dict(self):
        svc_yaml = {
           'external': self.external,
           'name': self.name,
           'portRange': self.port_range,
           'protocol': self.protocol.upper(),
         } 
        if self.device != None:
            svc_yaml['device'] = self.device
        return svc_yaml

class NetworkDevice:
    def __init__(self, **kwargs):
        self.name = from_kwargs(kwargs, 
                       'name', 
                       Exception('Missing required field: name'))
        self.controller = from_kwargs(kwargs, 'controller', 'virtio')
        self.ip = from_kwargs(kwargs, 'ip', None)
        # Default public_ip to false.  Ravello will change 
        # this automatically based on configured services.
        self.public_ip = from_kwargs(kwargs, 'public_ip', True)
        self.mac = from_kwargs(kwargs, 'mac', None)
    def to_yaml_dict(self, index):
        yaml = {
          'name': self.name,
          'device' : {
              'index' : index,
              'deviceType' : 'virtio'
            },
          'ipConfig' : {
             'hasPublicIp' : self.public_ip
            }
         }
        reserved_ip = { 'reservedIp' : self.ip }
        if self.ip != None:
          yaml['ipConfig']['autoIpConfig'] = reserved_ip
        else:
          yaml['ipConfig']['autoIpConfig'] = None
        if self.mac != None:
          yaml['device']['useAutomaticMac'] = False
          yaml['device']['mac'] = self.mac
        else:
          yaml['device']['useAutomaticMac'] = True
        return yaml

class Vm:
    def __init__(self, **kwargs):
        # Parse kwargs
        self.name = str(kwargs['index']) + kwargs['name']
        self.tag = kwargs['name']
        self.description = \
           from_kwargs(
               kwargs, 
               'description', 
               "\"" + self.name + "\\nnohbac: true\\n\"")
        self.num_cpus = from_kwargs(kwargs, 'cpus', 1)
        self.memory_size = from_kwargs(kwargs, 'ram', 2)
        self.memory_unit = from_kwargs(kwargs, 'mem_unit', "GB")
        self.keypair_name= from_kwargs(kwargs, 'keypair_name', None)
        self.keypair_id = from_kwargs(kwargs, 'keypair_id', None)
        self.hostnames = \
            from_kwargs(kwargs, 'hostname',
            [self.tag + ".example.com",
             self.tag])
        disks = from_kwargs(kwargs, 'disks', [{'size' : 40 }])
        self.stop_timeout = 300
        self.public_key = from_kwargs(kwargs, 'public_key', Exception("public_key required"))
        self.users = []
        self.hard_drives = []
        self.network_devices = []
        self.services = []
        # Ansible directives
        self.proxy = from_kwargs(kwargs, 'proxy', None)
        self.hostvars = from_kwargs(kwargs, 'ansible_vars', {})
        self.template_vars = from_kwargs(kwargs, 'template_vars', {})
        self.groups = from_kwargs(kwargs, 'groups', None)
        self.remote_user = from_kwargs(kwargs, 'remote_user', 'cloud-user')
        self.allow_nested= from_kwargs(kwargs, 'allow_nested', False)
        self.prefer_physical = from_kwargs(kwargs, 'prefer_physical', False)
        self.private_key_path = from_kwargs(kwargs, 'private_key_path', 
                            Exception("private_key_path required"))
        self.boot_disk_image = from_kwargs(kwargs, 'boot_image', DEFAULT_BOOT_IMAGE)
         
        if len(disks) == 0:
            raise Exception("There must be at least one disk")
        for i, d in enumerate(disks):
            d['index'] = i
            self.add_hard_drive(**d)
        nics = from_kwargs(kwargs, 'nics', [{'name' : 'eth0'}])
        for n in nics:
            self.add_network_device(**n)
        services = from_kwargs(kwargs, 'services', [])
        for s in services:
            if 'device' in s and not filter(lambda n: n.name == s['device'], 
                                       self.network_devices):
                raise Exception("No device: " + s['device'] + 'found for service: ' + s['name'])
              
            self.add_service(**s)
        # Add boot disk
        if not filter(lambda hd: hd.bootable, self.hard_drives):
            if self.hard_drives[0].image == '':
                self.hard_drives[0].image = self.boot_disk_image
            self.hard_drives[0].bootable = True
    def gen_ansible_directives(self):
        yml = {
          'name' : self.tag,
          'vars' : self.hostvars
        }
        yml['vars']['ansible_ssh_private_key_file'] = self.private_key_path
        yml['vars']['ansible_user'] = self.remote_user
        if self.groups != None:
            yml['groups'] = self.groups
        if self.proxy != None:
            yml['proxy'] = self.proxy
        return "#%ansible\n" + yaml.dump(yml, default_flow_style=False) + "#%end\n"
        
       
    def add_hard_drive(self, **kwargs):
        hd = HardDrive(**kwargs)
        self.hard_drives.append(hd)

    def add_service(self, **kwargs):
        s = Service(**kwargs)
        self.services.append(s)

    def add_network_device(self, **kwargs):
        nd = NetworkDevice(**kwargs)
        self.network_devices.append(nd)

    def to_yaml(self):
        vm_yaml = {
          'name' : self.name,
          'tag' : self.tag,
          'allowNested': self.allow_nested,
          'preferPhysicalHost' : self.prefer_physical,
          'description' : self.description + "\n" + self.gen_ansible_directives(),
          'numCpus' : self.num_cpus, 
          'memorySize': {
             'unit' : self.memory_unit,
             'value' : self.memory_size,
            }, 
          'hostnames' : self.hostnames if isinstance(self.hostnames, list) \
                                       else [self.hostnames],
          'supportsCloudInit' : True,
          'hardDrives' : [hd.to_yaml_dict(i) for i, hd in enumerate(self.hard_drives)],
          'suppliedServices' : [sv.to_yaml_dict() for i, sv in enumerate(self.services)],
          'networkConnections' : [nd.to_yaml_dict(i) for i, nd in enumerate(self.network_devices)],
          'userData' : """\
  #cloud-config
  ssh_pwauth: False
  disable_root: False
  users:
    - name: """ + self.remote_user + """
      sudo: ALL=(ALL) NOPASSWD:ALL
      lock_passwd: False
      ssh-authorized-keys:
      - """ + self.public_key
          }
        if self.keypair_id != None:
         vm_yaml['keypairId'] = int(self.keypair_id)
        if self.keypair_name != None:
          vm_yaml['keypairName'] = self.keypair_name
        return vm_yaml

class Template:
    def __init__(self):
        self.vm_list = []
    def add_vm(self, vm):
        self.vm_list.append(vm)
    def to_yaml(self):
      return { "vms" : [vm.to_yaml() for vm in self.vm_list] }

def gen_template(template):
    t = Template()
    for i, instance in enumerate(template):
        instance['index'] = i
        t.add_vm(Vm(**instance))
    return t
            
def main():
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.DEBUG)
    ### Optionally add a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    ### Add the console handler to the logger
    logger.addHandler(ch)    
    argument_spec=dict(
      path=dict(required=True, type='str'),
      instances=dict(required=True, type='list'),
      subnets=dict(required=False, type='list'))

    module = AnsibleModule(
        argument_spec=argument_spec)
    module_fail.attach_ansible_modle(module)
    filepath = module.params.get('path')
    instances= module.params.get('instances')
    subnets= module.params.get('subnets')
    t = gen_template(instances).to_yaml()
    if subnets:
        t['network'] = {}
        t['network']['subnets'] = subnets
    with open(filepath, "w") as f:
        f.write(yaml.safe_dump(t, default_flow_style=False))
    module.exit_json(msg="Created template: " + filepath)
    
main()

