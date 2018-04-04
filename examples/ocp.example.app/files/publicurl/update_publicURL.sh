#!/bin/bash

CFG="/etc/origin/master/master-config.yaml"

# This assumes the OSE master can log in to the workstation host without a password!
myExtIP=`ssh -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" 192.168.0.5 'curl -s http://www.opentlc.com/getip' 2>/dev/null`
if [ $? -ne 0 ]
then
        echo "Failed to get external IP"
        exit 1
fi

datest=`date +%Y%m%d%H%M`
cp $CFG $CFG.$datest

sed -i "s/masterPublicURL: .*$/masterPublicURL: https:\/\/$myExtIP:8443/" $CFG
sed -i "s/assetPublicURL: .*$/assetPublicURL: https:\/\/$myExtIP:8443\/console\//" $CFG
sed -i "s/publicURL: .*$/publicURL: https:\/\/$myExtIP:8443\/console\//" $CFG

systemctl restart atomic-openshift-master

