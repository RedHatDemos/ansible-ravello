# Ravello Ansible Module

## Accelerate Service Delivery Cloud Suite Demo
For usage and requirements of the Accelerate Service Delivery Cloud Suite Demo see: https://github.com/redhat-gpe/cloud_suite_fastrax/blob/master/modules/01_Overview/Lab_redhat-cloud-suite-deployment-demo.adoc

## Optimize IT Cloud Suite Demo
For usage and requirements of the Optimize IT Cloud Suite Demo see: https://github.com/redhat-gpe/cloud_suite_fastrax/blob/master/modules/01_Overview/Lab_redhat-cloud-suite-migration-demo.adoc

## Modernize Development and Operations Cloud Suite Demo
For usage and requirements of the Modernize Development and Operations Cloud Suite Demo see: https://github.com/redhat-gpe/cloud_suite_fastrax/blob/master/modules/01_Overview/Lab_redhat-cloud-suite-modernize-devops.adoc

## Scalable Infrastructure Cloud Suite Demo
For usage and requirements of the Scalable Infrastructure Cloud Suite Demo see: https://github.com/redhat-gpe/cloud_suite_fastrax/blob/master/modules/01_Overview/Lab_redhat-cloud-suite-deployment-demo.adoc

## Prerequisites
For instructions on setting up a system to use this repo see [Ravello_Ansible_module](Ravello_Ansible_module.adoc)

## Usage

The purpose of this project is to provide an Ansible python module to interact with the Ravello API via the Ravello SDK.

### Deploy an Environment

This playbook will create a blueprint based on a set of virtual machines described in *app_template.yml*. It will then create an application from this blueprint and wait for it to start.

To use the default values just run the *deploy_environment.yml*. 
```
ansible-playbook deploy_environment.yml 
```

NOTE: It is likely there may be a conflict if the default names have already been used. Instead, specify a *unique_name* and optionally a *version* which will be used to make sure your blueprints and applications have unique names

Specify *unique_name* and *version* if desired:
```
ansible-playbook deploy_environment.yml -e "unique_name=vvaldez-demo version=1.6"
```

It is also possible to load your own variables from a yaml file:
```
ansible-playbook deploy_environment.yml -e @vars.yml
```
Contents of *vars.yml*:
```
---
unique_name=vvaldez-demo
version=1.6
```

To skip the blueprint creation phase, just provide an existing *blueprint_id*:
```
ansible-playbook deploy_environment.yml -e "blueprint_id=12345678"
```
