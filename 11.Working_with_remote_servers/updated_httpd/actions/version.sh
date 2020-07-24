#!/bin/bash
OSID=$(cat /etc/os-release | grep -w "ID" | cut -d "=" -f 2)
OSID=${OSID%\"}
OSID=${OSID#\"}
if [[ "${OSID}" == "ubuntu" ]]
then
  echo "The os is identified as Ubuntu"
  apache2 -v | grep version | cut -d " " -f 3
elif [[ "${OSID}" == "rhel" ]]
then
  echo "The os is identified as RHEL"
   httpd -v | grep version | cut -d " " -f 3
else
  echo "The os is unkown"
  exit 5
fi

