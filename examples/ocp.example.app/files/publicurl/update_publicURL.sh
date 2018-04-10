#!/bin/bash

bastion="bastion.example.com"

echo "waiting for bastion availability"

while ! ssh root@$bastion; do
  sleep 5
done

cfg_dir="/etc/origin/master"
master_cfg="$cfg_dir/master-config.yaml"
console_cfg="$cfg_dir/webconsole-config.yaml"

myExtIP=`curl -s http://www.opentlc.com/getip`
myGUID=`ssh root@$bastion hostname|cut -f2 -d-|cut -f1 -d.`

echo "Updating public URLs"

# Just a couple of functions for motd change
# could be written with 'case' or 'if's but this is easier to read and change

function dev_motd {

cp /etc/motd /etc/motd.orig
cat << EOF >/etc/motd
#####################################################################################
##                                                                                 ##
##          Welcome to Red Hat Openshift Container Platform 3.9 workshop           ##
##                                                                                 ##
#####################################################################################
Information about Your current environment:
OCP WEB UI access via IP: https://$myExtIP:8443
Wildcard FQDN for apps: *.$myExtIP.xip.io
EOF
}

function prod_motd {

cp /etc/motd /etc/motd.orig
cat << EOF >/etc/motd
#####################################################################################
##                                                                                 ##
##          Welcome to Red Hat Openshift Container Platform 3.9 workshop           ##
##                                                                                 ##
#####################################################################################
Information about Your current environment:
Your GUID: $myGUID
OCP WEB UI access via IP: https://infranode-$myGUID.generic.opentlc.com:8443
Wildcard FQDN for apps: *.apps-$myGUID.generic.opentlc.com
EOF
}


shopt -s nocasematch
if [ $? -ne 0 ]
then
        echo "Failed to get external IP"
        exit 1
fi

ocp_config="/root/.kube/config"
datest=`date +%Y%m%d%H%M`
cp $master_cfg $master_cfg.$datest
oc --config $ocp_config -n openshift-web-console get configmap  webconsole-config -o yaml > $console_cfg

# Setting a router subdomain based on deployment (DEV vs. RHPDS)
echo "IP: $myExtIP"
echo "GUID: $myGUID"

if [[ $myGUID == 'repl' ]]
then
  for CFG in $master_cfg $console_cfg; do
    sed -i "s/masterPublicURL: .*$/masterPublicURL: https:\/\/$myExtIP:8443/" $CFG
    sed -i "s/assetPublicURL: .*$/assetPublicURL: https:\/\/$myExtIP:8443\/console\//" $CFG
    sed -i "s/consolePublicURL: .*$/consolePublicURL: https:\/\/$myExtIP:8443\/console\//" $CFG
    sed -i "s/publicURL: .*$/publicURL: https:\/\/$myExtIP:8443\/console\//" $CFG
    sed -i "s/subdomain: .*$/subdomain: $myExtIP.xip.io/" $CFG
  done
  dev_motd
else
  for CFG in $master_cfg $console_cfg; do
    sed -i "s/subdomain: .*$/subdomain: apps-$myGUID.generic.opentlc.com/" $CFG
    sed -i "s/masterPublicURL: .*$/masterPublicURL: https:\/\/infranode-$myGUID.generic.opentlc.com:8443/" $CFG
    sed -i "s/assetPublicURL: .*$/assetPublicURL: https:\/\/infranode-$myGUID.generic.opentlc.com:8443\/console\//" $CFG
    sed -i "s/consolePublicURL: .*$/consolePublicURL: https:\/\/infranode-$myGUID.generic.opentlc.com:8443\/console\//" $CFG
    sed -i "s/publicURL: .*$/publicURL: https:\/\/infranode-$myGUID.generic.opentlc.com:8443\/console\//" $CFG
  done
  prod_motd
  sleep 15
fi
oc --config $ocp_config -n openshift-web-console create -f $console_cfg --dry-run -o yaml | oc --config $ocp_config -n openshift-web-console replace -f -
oc --config $ocp_config -n openshift-web-console delete -n openshift-web-console `oc --config $ocp_config -n openshift-web-console get pod -o name`

sleep 15
echo "Recreating pod"
systemctl restart atomic-openshift-master-controllers atomic-openshift-master-api

scp -oStrictHostKeyChecking=no /etc/motd root@bastion.example.com:/etc/motd

