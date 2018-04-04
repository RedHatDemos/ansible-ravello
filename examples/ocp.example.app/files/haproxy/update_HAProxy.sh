#!/bin/bash

CFG="/etc/haproxy/haproxy.cfg"

# This assumes the OSE master can log in to the workstation host without a password!
myExtIP=`curl -s http://www.opentlc.com/getip`
if [ $? -ne 0 ]
then
        echo "Failed to get external IP"
        exit 1
fi

datest=`date +%Y%m%d%H%M`
cp $CFG $CFG.$datest

sed -i "s/ Location:.*$/ Location:\\\ http:\/\/$myExtIP:8080\\\1 if hdr_location/" $CFG

systemctl restart haproxy
