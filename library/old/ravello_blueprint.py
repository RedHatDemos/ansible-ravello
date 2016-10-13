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
module: ravello_blueprint
short_description: Manages an application blueprint in Ravello
description:
     - TBD
options:
  name:
    description:
      - application name
    required: true
  description:
    description:
      - application description
    required: false
  state:
    description:
     - Indicate desired state of the blueprint.
    default: present
    choices: ['present', 'absent']
    required: false
  username:
    description:
      - Ravello system username
    required: true
  password:
    description:
      - Ravello system password
    required: true
  app_name:
    description:
      - The name of an existing Ravello application to source when creating the blueprint.
      - Required if C(state) is present
    required: false
notes:
- QUESTION -- allow C(state) "present" without an C(app_name) to check if a blueprint exists, but don't create it instead return failed?
'''

EXAMPLES = '''
# Create a blueprint from an application
- ravello_blueprint:
    name: 'some-rav-app.bp'
    username: admin
    password: secret
    description: 'A test Ravello blueprint using Ansible'
    app_name: 'some-rav-app'
    state: present

# Check the blueprint exists (See QUESTION in Notes)
- ravello_blueprint:
    name: 'some-rav-app.bp'
    username: admin
    password: secret
    state: present

# Delete a blueprint
- ravello_blueprint:
    name: 'some-rav-app.bp'
    username: admin
    password: secret
    state: absent
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
        state=dict(default='present', choices=['present', 'absent']),
        username=dict(required=True),
        password=dict(required=True),
        app_name=dict(default=None),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
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


# import module snippets
from ansible.module_utils.basic import *

main()
