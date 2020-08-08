#!/bin/bash
Body=$1
Subject=$2
ToMail=$3
echo "$Body" | mail -s "$Subject" "$ToMail"
