#!/bin/bash
OSID=$(cat /etc/os-release  | grep -w "ID"| cut -d "=" -f 2)
OSID=${OSID%\"}
OSID=${OSID#\"}
if [[ "${OSID}" == "ubuntu" ]]
then
  echo "The OS is identified as Ubuntu"
  which apache2
elif [[ "${OSID}" == "rhel" ]]
then
  echo "The OS is identified as RHEL"
  which httpd
else
  echo "The OS is Unknown"
  exit 5
fi
