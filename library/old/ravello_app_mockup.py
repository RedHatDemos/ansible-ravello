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

try:
    from ravello_sdk import *
    HAS_RAVELLO_SDK = True
except ImportError:
    HAS_RAVELLO_SDK = False

def main():
    argument_spec = dict(
        name=dict(required=True),
        description=dict(default=None),
        state=dict(default='present', choices=['present', 'absent', 'started', 'stopped', 'restarted']),
        username=dict(required=True),
        password=dict(required=True),
        blueprint=dict(default=None),
        app_template=dict(default=None, type='path'),
        preferred_cloud=dict(default=None),
        preferred_region=dict(default=None),
        optimization_level=dict(default='cost', choices=['cost', 'performance']),
        application_ttl=dict(default='-1', type='int'),
        wait=dict(default=True, type='bool'),
        wait_timeout=dict(default=600, type='int'),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[['blueprint', 'app_template']],
        # We really really should support this...
        # supports_check_mode = True
    )
    if not HAS_RAVELLO_SDK:
        module.fail_json(msg='ravello_sdk required for this module')

    # NOT IN DOCS/SPECS. Do we want to add this though?
    # username = module.params.get('username', os.environ.get('RAVELLO_USERNAME', None))
    # password = module.params.get('password', os.environ.get('RAVELLO_PASSWORD', None))

    # ravello = RavelloClient(username, password, URL???)

    # EXAMPLE of how you'd detect check mode
    # if module.check_mode:
    #    pass

    # Example of response to controller...
    # return module.exit_json(changed=changed, msg=out_clean, rc=rc, whatever=whatever)

    state = module.params['state']
    if state == 'absent':

# import module snippets
from ansible.module_utils.basic import *

main()
