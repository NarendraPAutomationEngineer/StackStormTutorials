#!/bin/bash
ToMail=$1
Subject=$2
Body=$3
Attach=$4
echo "$Body" | mail -s "$Subject" $ToMail -A $Attach
