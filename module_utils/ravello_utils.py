#!/usr/bin/env python

import re
import yaml
import json
import sys
import random
import string
import os
import base64
import getpass
import logging
import logging.handlers


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
module_fail = ModuleFail()

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

# Ensure all required kwargs are present
def kwargs_check(kwargs, key_list, fn_name):
    for x in key_list:
        if x not in kwargs:
            raise Exception("Missing required keyword argument: " + x)
    for y in kwargs:
        if y not in key_list:
            raise Exception("Invalid keyword argument: " + y)

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

def json_path_contains(json_item, jspath):
    def recur(json_slice, split_path):
        if len(split_path) > 1:
            if not json_head_contains(json_slice, maybe_digit(split_path[0])):
                return False
            return recur(json_slice[maybe_digit(split_path[0])], split_path[1:])
        elif len(split_path) == 1:
            if not json_head_contains(json_slice, maybe_digit(split_path[0])):
                return False
            return True
        else:
            raise Exception("Error: invalid json path string")
    return recur(json_item, re.split(r'(?<!\\)\.', jspath))

