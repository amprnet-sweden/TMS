#FROM eclipse-temurin:21.0.9_10-jre-noble
FROM --platform=linux/amd64 eclipse-temurin:21.0.9_10-jre-noble AS build-amd64
FROM --platform=linux/arm64 eclipse-temurin:21.0.9_10-jre-noble AS build-arm64
FROM --platform=linux/arm/v7 arm32v7/eclipse-temurin:17.0.13_11-jre-jammy AS build-arm
FROM build-$TARGETARCH

ARG TARGETARCH

ARG JAR=tms-backend-3.0.0-SNAPSHOT.jar
ARG DIR=/opt/tms

ENV JAVA_OPTS="-Xms200m -Xmx200m -Dspring.profiles.active=docker -Djava.security.egd=file:/dev/./urandom"
ENV APP_DIR="${DIR}"

RUN groupadd -g 1005 tms && useradd -M -u 1005 -g tms tms

RUN mkdir -p ${DIR}/data ${DIR}/certs

ADD ./build/libs/$JAR ${DIR}/app.jar
ADD ./docker/entrypoint.sh ${DIR}/entrypoint.sh
RUN chmod 750 ${DIR}/entrypoint.sh
RUN chown -R tms:tms ${DIR}

WORKDIR ${DIR}

ENTRYPOINT ["/opt/tms/entrypoint.sh"]
CMD ["/opt/tms/app.jar"]

EXPOSE 8080
