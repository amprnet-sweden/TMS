#!/usr/bin/env bash

BASEDIR=$(dirname "$0")
KEYTOOL=/opt/java/openjdk/bin/keytool
ALIAS=amprnettmsdevca

if [ "$1" = "-trustca" ]; then
  shift
  ${KEYTOOL} -list -cacerts -alias ${ALIAS} >/dev/null

  if [ $? -ne 0 ]; then
    ${KEYTOOL} -import -v -noprompt \
      -alias ${ALIAS} -file ./certs/ca.crt \
      -cacerts -trustcacerts -storepass changeit
  fi

  su tms -c "exec /opt/java/openjdk/bin/java -jar $JAVA_OPTS $*"
else
  exec java -jar $JAVA_OPTS $*
fi
