#!/bin/bash
if [[ -f /etc/os-release ]]
then
   cat /etc/os-release | grep -w "ID" | cut -d "=" -f 2
else
   echo "/etc/os-release find not found" 1>&2 
   exit 2
fi
