#!/bin/bash

which httpd 1>/dev/null 2>/dev/null
if [[ $? -eq 0 ]]
then
   httpd -v | grep version | cut -d " " -f 3
else
   exit 1
fi

