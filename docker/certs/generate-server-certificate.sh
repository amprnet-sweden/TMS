#!/usr/bin/env bash

docker run --rm -it --name openssl --network none -v $PWD:/certs \
    alpine/openssl:3.5.2 req -x509 -nodes -days 365 \
    -CA /certs/ca.crt -CAkey /certs/ca.key \
    -subj "/C=SE/O=AMPRNet/OU=Development/CN=host.docker.internal" \
    -addext "subjectAltName=DNS.1:host.docker.internal,IP:127.0.0.1" \
    -newkey rsa:2048 -keyout /certs/private.key -out /certs/public.crt

chmod 644 /certs/private.key
