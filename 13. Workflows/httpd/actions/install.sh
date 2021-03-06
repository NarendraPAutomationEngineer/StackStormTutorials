#!/bin/bash
OSID=$(cat /etc/os-release | grep -w "ID" | cut -d "=" -f 2)
OSID=${OSID%\"}
OSID=${OSID#\"}
if [[ "${OSID}" == "ubuntu" ]]
then
  echo "The os is identified as Ubuntu"
  apt-get install apache2 -y
elif [[ "${OSID}" == "rhel" ]]
then
  echo "The os is identified as RHEL"
  yum install httpd -y
else
  echo "The os is unkown"
  exit 5
fi

