#!/usr/bin/python
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

DOCUMENTATION = '''
---
module: ravello_app
short_description: Manages a published application in Ravello 
description:
     - TBD
options:
  name:
    description:
      - Unique application instance name
    required: true 
  description:
    description:
      - Application instance description that will be set on creation
    required: false
  state:
    description:
      - Indicate desired state of the application instance.
    default: present
    choices: ['present', 'absent', 'started', 'stopped', 'restarted']
    required: false
  username:
    description:
      - Ravello system username
    required: true
  password:
    description:
      - Ravello system password
    required: true
  blueprint:
    description:
      - Create application instance based on an existing blueprint. See note below.
    required: false
  app_template:
    description:
      - Create application instance based on a app template. See note below.
    required: false
  preferred_cloud:
    description:
      - Preferred cloud provider to publish the Ravello application if creation is needed. 
  preferred_region:
    description:
      - Preferred region to publish the Ravello application if creation is needed.
    required: false
  optimization_level:
    description:
      - TBD
    default: cost
    required: false
    choices: ['cost', 'performance']
  application_ttl:
    description:
      - Ravello application autostop defined in minutes
    required: false
    default: -1
  wait:
    description:
      - Wait for the Ravello application to be in state 'running' before returning.
    default: True
    required: false
    choices: [ True, False ]
  wait_timeout:
    description:
      - How long before wait gives up, in seconds.
    required: false
    default: 600
notes:
  - C(app_template) and C(blueprint) are mututally exclusive. One of which is required when C(state) is present or started where creation of a Ravello application may need to occur.
  - Publishing preferences, C(preferred_cloud), C(preferred_region) and C(optimization_level), are only considered when initially published. Using different values will not change the publishing state of the Ravello application.  
  '''

EXAMPLES = '''
# Publish and launch application from an app template
- ravello_app:
    name: "unique-rav-app"
    app_template: /path/to/ravello_app.template
    username: admin
    password: secret
    state: started

# Publish and launch application from an existing blueprint 
- ravello_app:
    name: "unique-rav-app"
    blueprint: "existing-rav-app.bp"
    username: admin
    password: secret
    state: started

# Publish application with preferences and auto stop after 2 days
- ravello_app:
    name: "unique-rav-app"
    blueprint: "existing-rav-app.bp"
    username: admin
    password: secret
    preferred_region: Oregon
    preferred_cloud: AMAZON
    optimization_level: performance
    application_ttl: 2880
    state: started

# QUESTION: WHAT IF STARTED THEN PRESENT CALLED? RESPOND OK AND NO CHANGES? ERROR?
# Publish application but do not start VMs
- ravello_app:
    name: "unique-rav-app"
    app_template: /path/to/ravello_app.template
    username: admin
    password: secret
    state: present 

# Stop application
- ravello_app:
    name: "unique-rav-app"
    username: admin
    password: secret
    state: stopped 

# Stop and delete application
- ravello_app:
    name: "unique-rav-app"
    username: admin
    password: secret
    state: absent 

# Restart application
- ravello_app:
    name: "unique-rav-app"
    username: admin
    password: secret
    state: restarted

'''

