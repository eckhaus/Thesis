#!/bin/bash

ID=$(docker ps -aqf "NAME=$1")
echo $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $ID):8000
