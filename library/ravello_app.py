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
    required: yes
  description:
    description:
      - Application instance description that will be set on creation
  state:
    description:
      - Indicate desired state of the application instance.
    default: present
    choices: ['present', 'absent', 'started', 'stopped', 'restarted']
  username:
    description:
      - Ravello system username
    required: yes
  password:
    description:
      - Ravello system password
    required: yes
  blueprint:
    description:
      - Create application instance based on an existing blueprint
      - Is mututally exclusive with app_template, one of which is required for present or started where creation of a Ravello application may occur
  app_template:
    description:
      - Create application instance based on a app template.
      - Is mututally exclusive with blueprint, one of which is required for present or started where creation of a Ravello application may occur.
  preferred_cloud:
    description:
      - Preferred cloud provider to publish the Ravello application if creation is needed. 
  preferred_region:
    description:
      - Preferred region to publish the Ravello application if creation is needed.
  optimization_level:
    description:
      - TBD
    default: cost
    choices: ['cost', 'performance']
  application_ttl:
    description:
     - Ravello application autostop defined in minutes
    default: -1
  wait:
    description:
     - Wait for the Ravello application to be in state 'running' before returning.
    default: True
    choices: [ True, False ]
  wait_timeout:
    description:
     - How long before wait gives up, in seconds.
    default: 600
'''

EXAMPLES = '''
'''

