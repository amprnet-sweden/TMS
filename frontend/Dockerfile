FROM node:20.19-alpine3.22 AS builder

ENV NODE_ENV=production

RUN mkdir -p /usr/src/app/dist
WORKDIR /usr/src/app

COPY package.json .
COPY jsconfig.json .
COPY vite.config.mjs .
COPY .env.production .
COPY .eslintrc.js .
COPY public ./public
COPY src ./src
COPY index.html .

RUN npm install --include=dev
RUN npm run build

FROM nginx:1.29-alpine

COPY --from=builder --chown=nginx:nginx /usr/src/app/dist/ /usr/share/nginx/html/tms

RUN mkdir -p /etc/nginx/certs

ADD ./docker/nginx.conf /etc/nginx/nginx.conf
ADD ./docker/docker.conf /etc/nginx/conf.d/docker.conf

EXPOSE 9003
