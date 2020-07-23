#!/bin/bash
ToMail=$1
Subject=$2
Body=$3
echo "$Body" | mail -s "$Subject" $ToMail
