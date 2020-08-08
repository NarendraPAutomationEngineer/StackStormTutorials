#!/bin/bash
OSID=$(cat /etc/os-release  | grep -w "ID"| cut -d "=" -f 2)
OSID=${OSID%\"}
OSID=${OSID#\"}
if [[ "${OSID}" == "ubuntu" ]]
then
  echo "The OS is identified as Ubuntu"
  systemctl start apache2
elif [[ "${OSID}" == "rhel" ]]
then
  echo "The OS is identified as RHEL"
  systemctl start httpd
else
  echo "The OS is Unknown"
  exit 1
fi


