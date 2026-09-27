#!/usr/bin/env bash

docker run --rm -it --name openssl --network none -v $PWD:/certs \
    alpine/openssl:3.5.2 \
    genrsa -out /certs/ca.key 4096
docker run --rm -it --name openssl --network none -v $PWD:/certs \
    alpine/openssl:3.5.2 \
    req -x509 -new -nodes -key /certs/ca.key -sha256 -days 730 -subj "/C=SE/O=AMPRNet/OU=Development/CN=AMPRNet TMS Root CA" -out /certs/ca.crt

chmod 644 /certs/ca.key
