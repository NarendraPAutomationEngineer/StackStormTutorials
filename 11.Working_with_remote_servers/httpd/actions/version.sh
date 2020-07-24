#!/bin/bash
OSID=$(cat /etc/os-release  | grep -w "ID"| cut -d "=" -f 2)
OSID=${OSID%\"}
OSID=${OSID#\"}
if [[ "${OSID}" == "ubuntu" ]]
then
  echo "The OS is identified as Ubuntu"
  apache2 -v  | grep version | cut -d " " -f 3 
elif [[ "${OSID}" == "rhel" ]]
then
  echo "The OS is identified as RHEL"
  httpd -v| grep version | cut -d " " -f 3
else
  echo "The OS is Unknown"
  exit 5
fi



