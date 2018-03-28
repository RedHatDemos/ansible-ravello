#!/bin/env bash

if [[ $1 == '--list' ]]; then
  python /virt/nfs/ansible-ravello/inventory/ravello.py --list my.ravello.app
elif [[ $1 == '--hosts' ]]; then
  python /virt/nfs/ansible-ravello/inventory/ravello.py --hosts
fi
