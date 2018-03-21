#!/usr/bin/env python

import re
import yaml
import json

class ModuleFail:
    def __init__(self):
        self.module = None
    def attach_ansible_modle(self, module):
        self.module = module
    def __call__(self, msg):
        if (self.module == None):
            raise Exception(msg)
        else:
            self.module.fail_json(msg=msg)

def maybe_digit(item):
    if (item.isdigit()):
      return int(item)
    else:
      return item

def ravello_template_set(json_slice, jspath_str, value):
    jspath = re.split(r'(?<!\\)\.', jspath_str)
    def recur (json_slice, jspath, value):
        if len(jspath) > 1:
            if not json_head_contains(json_slice, maybe_digit(jspath[0])):
                if jspath[1].isdigit():
                    json_slice = json_insert_head(json_slice, maybe_digit(jspath[0]), [])
                else:
                    json_slice = json_insert_head(json_slice, maybe_digit(jspath[0]), {})
            json_insert_head(json_slice, maybe_digit(jspath[0]),
                        recur(json_slice[maybe_digit(jspath[0])], 
                            jspath[1:], value))
        elif len(jspath) == 1:
            json_slice = json_insert_head(json_slice, maybe_digit(jspath[0]), value)
        else:
            raise Exception("Error: invalid json path string: " + jspath_str)
        return json_slice
    return recur(json_slice, jspath, value)
def json_insert_head(json_slice, key, value):
    if type(key) is int:
        if len(json_slice) <= key:
          json_slice.insert(key, value)
        else:
            json_slice[key] = value
    else:
        json_slice[key] = value
    return json_slice

# return kwargs[k] if it exists,
# otherwise return default
def from_kwargs(kwargs, k, default):
    if k in kwargs:
        return kwargs[k]
    elif type(default) is Exception:
        raise default
    else:
      return default

def json_head_contains(json_item, key):
    if json_item is None:
        return False
    if type(key) is int:
        if len(json_item) <= key:
          return False
        else:
            return True
    else:
        return (key in json_item)

def ravello_template_get(json_item, jspath_str, **kwargs):
    jspath = re.split(r'(?<!\\)\.', jspath_str)
    def recur(json_slice, jspath):
        if len(jspath) > 1:
            if not json_head_contains(json_slice, maybe_digit(jspath[0])):
                raise Exception("error: invalid json_path string: " + jspath_str)
            return recur(json_slice[maybe_digit(jspath[0])], jspath[1:])
        elif len(jspath) == 1:
            if not json_head_contains(json_slice, maybe_digit(jspath[0])):
                raise Exception("error: invalid json_path string: " + jspath_str)
            else:
                return json_slice[maybe_digit(jspath[0])]
        else:
            raise exception("error: invalid json_path string: " + jspath_str)
    return recur(json_item, jspath)

def check_for_param(json_item, jspath, **kwargs):
    full_jspath = jspath
    def cfp_helper(json_item, jspath, **kwargs):
         valid = from_kwargs(kwargs, 'valid_options', []) 
         fail_msg = from_kwargs(kwargs, 'fail_msg',
                 "Template Error: " + full_jspath + " - Missing or invalid.\nIn json item: "  + json.dumps(json_item))
         required = from_kwargs(kwargs, 'required', True)
         if type(valid) is str:
             valid = [valid]
         if type(valid) is list:
             valid_list = valid
             valid = lambda val: val in valid_list
         if not callable(valid):
             raise Exception('Error: `valid` kwarg must of type string, list, or parity 1 function')
         def recur(json_slice, jspath):
             if type(jspath) is str:
               jspath = re.split(r'(?<!\\)\.', jspath)
             if len(jspath) > 1:
                 if not json_head_contains(json_slice, maybe_digit(jspath[0])):
                     if not required:
                         return False
                     if 'default_if_missing' in kwargs:
                         ravello_template_set(json_item, '.'.join(jspath), value)
                     module_fail(fail_msg)
                 return recur(json_slice[maybe_digit(jspath[0])], jspath[1:])
             elif len(jspath) == 1:
                 if not json_head_contains(json_slice, maybe_digit(jspath[0])):
                     if not required:
                         return False
                     if 'default_if_missing' not in kwargs:
                       module_fail(fail_msg)
                     else:
                       json_insert_head(json_slice, maybe_digit(jspath[0]),
                               kwargs['default_if_missing'])
                 if 'valid' not in kwargs:
                     return True
                 else:
                     return valid(json_slice[maybe_digit(jspath[0])])
             else:
                 raise Exception("Error: invalid json path string")
         return recur(json_item, jspath)
    return cfp_helper(json_item, jspath, **kwargs)

module_fail = ModuleFail()
