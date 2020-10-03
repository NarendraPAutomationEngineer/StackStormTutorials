#!/bin/bash

sleep 61
pkg=$1


osName=$(cat /etc/*release |grep -w "ID"|cut -d= -f2|tr -d '"')

if [[ "${osName}" == "rhel" ]]
then
	yum install $pkg -y
	exit 0
fi

if [[ "${osName}" == "ubuntu" ]]
then
	apt-get install $pkg -y
	exit 0
fi

echo "This is new OS" 1>&2
exit 5
