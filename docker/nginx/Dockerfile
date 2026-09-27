FROM nginx:1.29

RUN apt-get update && apt-get install -y openssl gnupg2 apt-transport-https wget

ADD ./ca.key /etc/ssl/certs/TMS-Dev-CA.key
ADD ./ca.crt /etc/ssl/certs/TMS-Dev-CA.crt

RUN openssl req -x509 -nodes -days 90 -CA /etc/ssl/certs/TMS-Dev-CA.crt -CAkey /etc/ssl/certs/TMS-Dev-CA.key -subj "/C=SE/O=AmprNet/OU=Development/CN=tms.amprnet.se" -addext "subjectAltName=DNS.1:host.docker.internal,IP:127.0.0.1" -newkey rsa:2048 -keyout /etc/ssl/private/nginx-selfsigned.key -out /etc/ssl/certs/nginx-selfsigned.crt

RUN rm -f /etc/ssl/certs/TMS-Dev-CA.key

ADD nginx.conf /etc/nginx/nginx.conf
ADD docker.conf /etc/nginx/conf.d/default.conf
#ADD docker.conf /etc/nginx/conf.d/docker.conf

ENV NGINX_PORT=9003

EXPOSE 9003

#CMD ["nginx", "-g", "daemon off;"]
