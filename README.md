# TMS
AMPRNet SE Ticket Management System

# System Overview

TMS is a web application that communicates with a backend service via REST API.

```
               +-------------+
               | Web Browser |
               |             |
               |     TMS     |
               +-------------+
                      ^
                      |
                      |
                      v
            +-------------------+
            |   Reverse Proxy   |
            |                   |
            | (NGINX or Apache) |
            +-------------------+
                  ^      |
                  |      |
           +------+      +-----+
           |                   |
           v                   v
    +-------------+     +-------------+
    |   Backend   |     |   Identity  |
    |   Service   |---->|   Provider  |
    |(Spring Boot)|     |  (Keycloak) |
    +-------------+     +-------------+
           ^                   ^
           |                   |
           v                   v
        +-------------------------+
        |         Database        |
        |                         |
        |        (MariaDB)        |
        +-------------------------+
```

Everything is configurable. For example, the identity provider can be an external IdP shared by 
many other services.
The database can also be shared by other services.
The following installation instructions however assume all components are installed together
with TMS as the sole consumer.

# Installation options

You could deploy TMS in multiple ways. here are som popular ways to install a complete TMS system:

## Run pre-built Docker images

### Clone TMS git repository

In order to run TMS under docker, the TMS git repository must first be cloned.

```
git clone https://github.com/amprnet-sweden/TMS.git
cd TMS
```
### Install Docker

    sudo curl -sSL https://get.docker.com | sh

Add **host.docker.internal** as alias for 127.0.0.1 in /etc/hosts

    vi /etc/hosts

Make Docker available for current user.

    sudo usermod -aG docker ${USER}

You may have to logout and login to enable the new group.

### Login to AMPRNet GitHub Container Registry

    docker login ghcr.io/amprnet-sweden

Password is your GitHub personal token (Settings -> Developer Settings -> Personal access tokens, use Classic token)

### Option 1 (the easy way): Start TMS application and dependent services with Docker Compose

TMS depends on the following services:

- **MariaDB**, MySQL or PostgreSQL server for persistence
- **Keycloak** for managing authentication, users, roles and permissions
- **NGINX** or Apache HTTPd for routing HTTP requests

To start TMS on a local computer, the easiest way is to use **docker compose** to bring up all services at once.
A `docker-compose.yml` file is located in the root of this repository.

However, TLS is mandatory so you need to provide certificates for the environment where you will run TMS.
For local development and testing you can generate self-signed certificates and configure NGINX to use them.
For public access you can use Let's Encrypt or buy a certificate from a commercial dealer.

#### Generate self-signed certificates

The section only applies to local development or test environments. For a public facing TMS instances,
use Let's Encrypt instead.

If you have not done so already, generate a self-signed **root certificate** with:
```
cd docker/certs
./generate-root-certificate.sh
```
Two files are created: `ca.key` and `ca.crt`

If you force your web browser to trust the root certificate (ca.crt) by importing it,
the browser will also trust other self-signed certificates that you generate with this root certificate as issuer.

Then generate the **server certificate** with:
```
cd docker/certs
./generate-server-certificate.sh
```

Copy ca.key and ca.crt to nginx folder.

    cp ca.{key,crt} ../nginx

#### Start services

Make sure you are located in the TMS root directory

    cd ../..

    docker compose up

##### Create service account

Create a service account for TMS in Keycloak https://host.docker.internal:9003/auth/admin

username=admin-cli, password=strong_password, realm=master

Note that the admin-cli user must be created in the **master** realm, not in the amprnet realm.

Assign two **client roles** to the admin-cli user:

- amprnet-realm query-users
- amprnet-realm view-users

This gives the admin-cli user in the master realm permission to query and view users in the **amprnet** realm.

Don't forget to set a strong password (credentials) for the admin-cli user.

##### Login

Access TMS on https://host.docker.internal:9003/tms and click **Register**.

The default amprnet realm has *self registration* enabled and users will get the *tms-superuser* role.
As soon as you have registered the first (super)user, you may want to disable *self registration* in Keycloak.

### Option 2: Run each Docker container separately

If you have a database server up and running already (MariaDB, MySQL, PostgreSQL) and you want to use it
for TMS you must configure the database connection in TMS by setting environment variables.

Example:
```
SPRING_DATASOURCE_URL=jdbc:my_sql_server://mariadb:3306/tms
SPRING_DATASOURCE_USERNAME=tms
SPRING_DATASOURCE_PASSWORD=hemligt
```

Same with Keycloak. If you have a Keycloak server up and running already, and you want to use it
for TMS you must configure the OIDC parameters in TMS by setting environment variables.

Example:
```
SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_ISSUER_URI=https://my_keycloak_server:8080/auth/realms/amprnet
```

NOTE that you can't use `localhost` for hostnames in the configuration above because
TMS backend is running inside a container, and localhost points to the container, not to the host system.

Keycloak is tricky because hostnames need to match the hostname in the TLS certificates used.

For the *Role Base Security* to work you must ensure that **Add to userinfo** is enabled in Keycloak
`Client scopes "roles" -> Mappers "realm roles"`

## Native installation with Ansible (preview)

For a dedicated Debian 13 ARM64 host, see the [Ansible installer](ansible/README.md).
It builds and installs the application, database, identity service and HTTPS proxy.
The documentation lists tested behavior and remaining acceptance work.

## Build from source code  (the hard way)

The instructions below are tested successfully on a Raspberry Pi 5 running Raspberry Pi OS.

Also tested on Raspberry Pi 3 running Raspbian Buster. However, that combination required Node.js 18 (see below).

### Clone TMS git repository

```
git clone https://github.com/amprnet-sweden/TMS.git
cd TMS
```
If you need to use SSH:
```
git clone git@github.com:amprnet-sweden/TMS.git
cd TMS
```

### Install Node.js (if not already installed)

```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
nvm install 22
```
If you get an error message `nvm not found`, logout and login then `nvm install 22` should work.

Node.js home page: https://nodejs.org/

###  Build frontend

Change current directory to 'frontend'.

`cd frontend`

Edit `.env.production` and set web address for the TMS application.

```
VITE_APP_AUTH='https://tms.mydomain.se/auth'
VITE_APP_API='https://tms.mydomain.se/api'
VITE_APP_WS='wss://tms.mydomain.se/api/ws'
```

Install frontend dependencies.

```
npm ci --include=dev
```

Build frontend.

```
npm run build
```

The ./**dist** folder now contains all JavaScript and HTML files for the frontend application.

NOTE: If you get the following error message when you run `npm install` you are running a very old version of Raspberry Pi OS.

`node: /usr/lib/arm-linux-gnueabihf/libstdc++.so.6: version `GLIBCXX_3.4.26' not found (required by node)`

If that is the case, install Node.js version 18 instead of 22 (`nvm install 18`).

### Install Java Development Kit (if not already installed)

The current source build uses JDK 21 for both Gradle and compilation. Use Java 21
for the native backend and Keycloak too; a separate JDK 17 installation is not needed.

#### Option 1: Let SDKMAN handle your Java installation (recommended)

```
sudo apt install zip
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 21.0.9-tem
```

**NOTE:** The current source build requires an OS that can run JDK 21. Older
Raspbian releases that only support older JDKs need an OS upgrade or a separately
validated older TMS release.

SDKMAN home page: https://sdkman.io

#### Option 2: Install Java manually

```
sudo apt install openjdk-21-jdk-headless
java -version
```

### Install MariaDB

```
sudo apt install mariadb-server

sudo mysql_secure_installation
```

#### Create keycloak and tms databases

```
sudo mysql -uroot -p

CREATE DATABASE keycloak CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER keycloak IDENTIFIED BY 'hemligt';
GRANT ALL ON keycloak.* TO keycloak;

CREATE DATABASE tms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER tms IDENTIFIED BY 'hemligt';
GRANT ALL ON tms.* TO tms;

FLUSH PRIVILEGES;
```

### Download and install Keycloak

TMS delegates all user management and authentication to an external identity provider (IdP).
Keycloak is a popular identity provider that we use for development and production.

Download Keycloak from https://www.keycloak.org/downloads

```
sudo mkdir -p /opt/keycloak
sudo cd /opt/keycloak
sudo wget https://github.com/keycloak/keycloak/releases/download/26.4.7/keycloak-26.4.7.tar.gz
sudo tar xf keycloak-26.4.7.tar.gz
```

**Create keycloak user and group**

```
sudo groupadd -g 1004 keycloak
sudo useradd -u 1004 -g keycloak keycloak -m -s /bin/bash
```

**Change ownership of all Keycloak files to user keycloak**

`sudo chown -R keycloak:keycloak /opt/keycloak`

**Create start script for Keycloak**

`sudo vi /opt/keycloak/start.sh`

Add the following content:
```
#!/usr/bin/env bash

set -e

KEYCLOAK_HOME=/opt/keycloak/keycloak-26.4.7

cd ${KEYCLOAK_HOME}

source /home/keycloak/.sdkman/bin/sdkman-init.sh

exec bin/kc.sh start --http-port=8088 --http-enabled=true --hostname-strict=false --proxy-headers=xforwarded \
    --http-relative-path=/auth --http-management-relative-path=/ --http-management-port=8090 \
    --cache=local $*
```

**Make script executable**

```
sudo chown keycloak:keycloak /opt/keycloak/start.sh
sudo chmod 750 /opt/keycloak/start.sh
```

**Create a systemd service script**

`sudo vi /lib/systemd/system/tms-keycloak.service`

Add the following content:
```
[Unit]
Description=Keycloak Identity Provider for TMS
After=network-online.target

[Service]
WorkingDirectory=/opt/keycloak
ExecStart=/opt/keycloak/start.sh
Type=simple
Restart=always
User=keycloak
Group=keycloak

[Install]
WantedBy=multi-user.target
```

#### Configure Keycloak
```
cd /opt/keycloak/keycloak-26.4.7
sudo vi conf/keycloak.conf     (set database parameters)
```

At minimum, the following three database parameters must be set in keycloak.conf

- db=mariadb
- db-username=keycloak
- db-password=hemligt


#### Import Realm config

To import clients and roles for the **amprnet** realm when Keycloak starts for the first time,
copy TMS/docker/keycloak/amprnet-realm.json to {keycloak directory}/data/import folder.
You must also add the `--import-realm` flag when you start Keycloak.

```
cd /opt/keycloak/keycloak-26.4.7
sudo mkdir -p data/import
sudo cp $HOME/TMS/docker/keycloak/amprnet-realm.json data/import/amprnet-realm.json
```

#### Install Java to be used by Keycloak

```
sudo su - keycloak
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 21.0.8-tem
```

#### Start Keycloak

While you have the **keycloak** user shell active, try to start Keycloak using the start script.

```  
export KC_BOOTSTRAP_ADMIN_USERNAME=admin
export KC_BOOTSTRAP_ADMIN_PASSWORD=strongpassword
/opt/keycloak/start.sh --import-realm
```

If Keycloak started ok, press CTRL-C to stop it.
You can now exit the **keycloak** user shell.

#### Enable Keycloak service

If Keycloak started ok, you can enable the systemd service so that Keycloak starts automatically at server boot.

```
sudo systemctl start tms-keycloak
sudo systemctl status tms-keycloak
sudo systemctl enable tms-keycloak
```

### Install NGINX

`sudo apt install nginx`

Modify and copy the following NGINX configuration to /etc/nginx/sites-available/tms.conf
then make a symlink from sites-available to sites-enabled.

```
cd /etc/nginx/sites-available
sudo vi tms      (insert config below)
cd ../sites-enabled
sudo ln -s ../sites-available/tms .
```

Change **server_name** and paths to your ssl certificate and key.
The rest of the configuration should work as is.

```
upstream keycloak {
    server 127.0.0.1:8088;
}
upstream backend {
    server 127.0.0.1:8080;
}
server {
    server_name tms.mydomain.se;

    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    ssl_certificate /etc/nginx/certs/public.crt;
    ssl_certificate_key /etc/nginx/certs/private.key;
    ssl_protocols    TLSv1.2 TLSv1.3;

    root /usr/share/nginx/html;

    location /tms/index.html {
        gzip_static on;
        etag on;
    }
    location /tms {
        try_files $uri $uri/ /tms/index.html;
        gzip_static on;
        etag on;
    }

    location ~ ^/auth/(?:js|realms|resources|admin).* {
        proxy_pass http://keycloak$request_uri;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Correlation-ID $request_id;
        proxy_set_header Origin $http_origin;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location ~ ^/api/(.+) {
        proxy_pass http://backend/$1$is_args$args;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Correlation-ID $request_id;
        proxy_set_header Origin $http_origin;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Copy all web client files in the `frontend/dist` folder to `/usr/share/nginx/html/tms`

```
cd $HOME/TMS/frontend/dist
sudo cp -r . /usr/share/nginx/html/tms
```

Make sure NGINX configuration syntax is ok

`sudo nginx -t`

Reload the configuration

`sudo systemctl reload nginx`

#### Install Let's Encrypt certbot

`sudo apt install -y certbot python3-certbot-nginx`

Create certificate for host.

`sudo certbot --nginx -d tms.mydomain.se --register-unsafely-without-email`

### Configure clients and add user in Keycloak

Open https://tms.mydomain.se/auth/admin in your browser and login to Keycloak using admin credentials that you set above.

- Configure address for **tms-web-app**
- Create a tms user that belongs to the group "TMS Superusers"

Client **tms-web-app** config:
```
Root URL: https://tms.mydomain.se/tms
Home URL: https://tms.mydomain.se/tms
Valid redirect URIs: https://tms.mydomain.se/tms/*
Web origins: https://tms.mydomain.se
Admin URL: https://tms.mydomain.se/tms
```

### Configure the TMS backend

Edit `backend/src/main/resources/application-default.yaml`

The following two configuration parameters are **important** to set correct:

```
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://tms.mydomain.se/auth/realms/amprnet
  datasource:
    url: jdbc:mariadb://localhost:3306/tms
    username: tms
    password: "PASSWORD"
tms:
  allowed-origins:
    - https://tms.mydomain.se          
```

#### Install Docker (if you want to run backend tests)

`sudo apt install docker.io`

Add current user to the docker group

`sudo usermod -aG docker $USER`

#### Build the backend
```
cd ./backend
./gradlew build
```

If the build succeeds, all Java classes required by the TMS backend are in `./build/libs/tms-backend-3.0.0-SNAPSHOT.jar`.

If you want to skip the tests you can run `./gradlew -x test build`

#### Configure TMS Backend Service

**Create tms user and group**

```
sudo groupadd -g 1005 tms
sudo useradd -u 1005 -g tms tms -m -s /bin/bash
```

Create /opt/tms to hold all backend files

```
sudo mkdir -p /opt/tms/config
cd 
sudo cp $HOME/TMS/backend/build/libs/tms-backend-3.0.0-SNAPSHOT.jar /opt/tms
sudo cp $HOME/TMS/backend/src/main/resources/application-default.yaml /opt/tms/config
```

**Change ownership of all backend files to user tms**

`sudo chown -R tms:tms /opt/tms`

**Create start script for TMS backend**

`sudo vi /opt/tms/start.sh`

Add the following content:
```
#!/usr/bin/env bash

set -e

TMS_HOME=/opt/tms

cd ${TMS_HOME}

source /home/tms/.sdkman/bin/sdkman-init.sh

exec java -Xms256m -Xmx256m -jar /opt/tms/tms-backend-3.0.0-SNAPSHOT.jar
```

**Make script executable**

```
sudo chown tms:tms /opt/tms/start.sh
sudo chmod 750 /opt/tms/start.sh
```

**Create a systemd service script**

`sudo vi /lib/systemd/system/tms-backend.service`

Add the following content:
```
[Unit]
Description=TMS Backend Service
After=network-online.target

[Service]
WorkingDirectory=/opt/tms
ExecStart=/opt/tms/start.sh
Type=simple
Restart=always
User=tms
Group=tms

[Install]
WantedBy=multi-user.target
```

#### Install Java to be used by TMS backend

```
sudo su - tms
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 21.0.8-tem
```

While you have the **tms** user shell active, try to start TMS using the start script.

```
/opt/tms/start.sh 
```

If TMS started ok, press CTRL-C to stop it.
You can now exit the **tms** user shell.

#### Enable TMS backend service

If TMS backend started ok, you can enable the systemd service so that TMS starts automatically at server boot.

```
sudo systemctl start tms-backend
sudo systemctl status tms-backend
sudo systemctl enable tms-backend
```

### Login to TMS web application

Access TMS on https://tms.mydomain.se/tms

You should be redirected to the login page (provided by Keycloak).
And once you logged in you should be presented with the TMS dashboard.

# REST API

**NOTE** The following instructions are accessing the "backend for frontend" API of TMS.
Because currently there is no official REST API. It's still in the backlog.
When a REST API is published we will update this section.

## Create an API client in Keycloak

Login to Keycloak admin console https://tms.mydomain.se/auth/admin
Then add a new **client**. This example creates a client called *curl*, but you can use any name.

- Client Type: **OpenID Connect**
- Client ID: **curl**
- Name: **cURL access to REST API**
- Client Authentication: **On**
- Authorization: **Off**
- Standard flow: **Unchecked**
- Service account roles: **Checked**

**Save** The client configuration and copy the **Client Secret** from the Credentials tab.

Paste the client secret into an environment variable.

```
CLIENT_ID=curl
CLIENT_SECRET=the-client-secret-that-you-copied-from-keycloak
MISSION_ID=the-id-of-the-mission-you-want-to-access (can be found in TMS web UI)
```

In Keycloak still on the curl client details page, select the tab **Service account roles** and assign a **tms-xxxxx** role to the client.

On the top of the "Service account roles" tab there is a text:
"To manage detail and group mappings, click on the username service-account-curl"

Click on the link `service-account-curl` to edit details about the service account.
Enter **email**, **Firstname** and **Lastname** for the service account.
Email must be unique within the realm.

**Now you are ready to access the REST API with cURL**

## Get an access token

Go back to the terminal where you set `CLIENT_ID` and `CLIENT_SECRET` environment variables.

**Request an access token**

```
curl -k -X POST -H 'Content-Type: application/x-www-form-urlencoded' -d grant_type=client_credentials \
    -d client_id=$CLIENT_ID -d client_secret=$CLIENT_SECRET \
    https://tms.mydomain.se/auth/realms/amprnet/protocol/openid-connect/token
```

You will get an access token printed in the terminal. Copy the string after "access_token": including the surrounding quotes.
{"access_token":**"eyJhbGciOiJSUzI1NiIs......."**,"expires_in":300}

Set an environment variable to the access token value.

`JWT="eyJhbGciOiJSUzI1NiIs......."`

## Make calls to the API

Now that you have the access token in an environment variable, it's easy to make cURL calls to the REST API.

**List incidents**

`curl -v -H "Authorization: Bearer $JWT" -H "x-tms-mission: $MISSION_ID" https://tms.mydomain.se/api/incidents`

**Create incident**

TBD

# Replication 

To obtain syncronization between a primary and a secondary spare server in this use case, we use MariaDB replication in combination with rsync. In the following scenario the primary server is located on a publicly accessible IP-address and the secondary behind a NAT, for example in a command centre. The MariaDB replication and rsync will be tunneled in a SSH tunnel initiated by the secondary server, so we don't expose MariaDB to big bad Internet.

Reference: https://mariadb.com/docs/server/ha-and-performance/standard-replication/setting-up-replication

## Prerequisites

Both primary and secondary servers are assumed having TMS set up according to above instructions. The replication has been tested in an environment running Ubuntu 24.

Needless to say, before you begin **make necessary backups!**

Before you begin, make sure that the tms and keycloak databases on both servers are identical. Do not work in tms or keycloak during this setup process.

On the primary server:

```
mysqldump -uroot -p tms --add-drop-database > /tmp/tms.sql
mysqldump -uroot -p keycloak --add-drop-database > /tmp/keycloak.sql
```

Copy the files to /tmp on the secondary server and import tms and keycloak databases into MariaDB:

```
mysql -uroot -p tms < tms.sql
mysql -uroot -p keycloak < keycloak.sql
```

### Secondary server

```
sudo apt install autossh rsync
```

The root user needs to have a SSH key without a passphrase, if none exists in /root/.ssh create one (press enter for passphrase):

```
sudo su
ssh-keygen -t ed25519
```

Copy the content of /root/.ssh/id_ed25519.pub to /root/.ssh/authorized_keys on the primary server. Don't forget to do (on the primary server):

```
chmod 400 /root/.ssh/authorized_keys
```

Verify that you can connect as root without password from the secondary to the primary server:

```
ssh root@tms.mydomain.com
exit
```

If the file /etc/letsencrypt/ssl-dhparams.pem doesn't exist on the secondary server, copy it from the primary.

Create the rsync script:

```
sudo vi /usr/local/bin/tms-sync.sh
```

Paste the following (change MASTER to your primary server's host name):

```
#!/bin/sh
# Syncs TMS needed files from current master to this server.
# Should be run by cron on mirror server only.
# Assumes that passwordless ssh connection can be established to 
# master server already.
# 2025-09-24 SM0RGM Stefan Helander sm0rgm@amprnet.se

# Master from which we are syncing
MASTER=tms.mydomain.com

# rsync
RSYNC=/usr/bin/rsync
# When testing manually use with progress 
RSYNCFLAGS="aPxv --progress"
#RSYNCFLAGS=aPxq

# ssh
SSH=/usr/bin/ssh

$RSYNC -e 'ssh' -$RSYNCFLAGS --ignore-missing-args --delete-during root@$MASTER:/opt/ /opt
$RSYNC -e 'ssh' -$RSYNCFLAGS --ignore-missing-args --delete-during root@$MASTER:/etc/nginx/sites-available/ /etc/nginx/sites-available
$RSYNC -e 'ssh' -$RSYNCFLAGS --ignore-missing-args --delete-during root@$MASTER:/etc/nginx/sites-enabled/ /etc/nginx/sites-enabled
$RSYNC -e 'ssh' -$RSYNCFLAGS --ignore-missing-args --delete-during root@$MASTER:/etc/letsencrypt/archive/ /etc/letsencrypt/archive
$RSYNC -e 'ssh' -$RSYNCFLAGS --ignore-missing-args --delete-during root@$MASTER:/etc/letsencrypt/live/ /etc/letsencrypt/live
$RSYNC -e 'ssh' -$RSYNCFLAGS --ignore-missing-args --delete-during root@$MASTER:/usr/share/nginx/html/tms/ /usr/share/nginx/html/tms
```

Make it executable:

```
chmod 700 /usr/local/bin/tms-sync.sh
```

Test the script:

```
/usr/local/bin/tms-sync.sh
```

If all works, edit the script and comment out the RSYNCFLAGS with progress option and uncomment the next one without progress. If needed, install rsync in the primary server first (see below).

Put the sync script and SSH tunnel commands in cron:

```
crontab -e
```

Paste the following (change to your host name of the primary server):

```
05 * * * * /usr/local/bin/tms-sync.sh > /dev/null
@reboot /usr/bin/autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -f -L 33306:localhost:3306 root@tms.mydomain.com
@reboot /usr/bin/autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -f -R 33306:localhost:3306 root@tms.mydomain.com
```

Reboot the secondary and verify that you can connect to the MariaDB server on the primary from the secondary and vice versa:

```
mysql -uroot -p --port=33306 -hlocalhost
````

Create the file:

```
sudo vi /etc/mysql/mariadb.conf.d/tms_replication.cnf
```

Paste the following (if you want replication of all databases, comment out replicate-do-db):

```
[mariadb]
log-bin
server_id=2
log-basename=replica2
replicate-do-db=keycloak,tms
binlog_format=mixed
```

Make sure that every server has a unique server_id!

Restart mariadb:

```
sudo systemctl restart mariadb
```

Start MariaDB command line client:

```
mysql -uroot -p
```

Create the replication user:

```
CREATE USER 'tms_replication_user'@'%' IDENTIFIED BY 'bigs3cret';
GRANT REPLICATION SLAVE ON *.* TO 'tms_replication_user'@'%';
FLUSH PRIVILEGES; FLUSH TABLES WITH READ LOCK;
SHOW MASTER STATUS;
UNLOCK TABLES;
QUIT;
```

Make a note of filename and position (needed on the primary). More steps are needed on the secondary later on but first the primary server must be configured.

### Primary server

```
sudo apt install rsync
```

Create the file:

```
sudo vi /etc/mysql/mariadb.conf.d/tms_replication.cnf
```

Paste the following (if you want replication of all databases, comment out replicate-do-db):

```
[mariadb]
log-bin
server_id=1
log-basename=master1
replicate-do-db=keycloak,tms
binlog-format=mixed
```

Make sure that every server has a unique server_id!

Restart mariadb:

```
sudo systemctl restart mariadb
```

Start MariaDB command line client:

```
mysql -uroot -p
```

Create the replication user:

```
CREATE USER 'tms_replication_user'@'%' IDENTIFIED BY 'bigs3cret';
GRANT REPLICATION SLAVE ON *.* TO 'tms_replication_user'@'%';
FLUSH PRIVILEGES; FLUSH TABLES WITH READ LOCK;
SHOW MASTER STATUS;
UNLOCK TABLES;
QUIT;
```

Make a note of filename and position (needed on the primary). More steps are needed on the primary later on.

Now, find the filename and position you noted from the secondary server.

Start MariaDB command line client:

```
mysql -uroot -p
```

Do the following but replace the log file name and position with the ones from your notes, from the secondary server:

```
RESET SLAVE;
CHANGE MASTER TO
  MASTER_HOST='localhost',
  MASTER_USER='tms_replication_user',
  MASTER_PASSWORD='bigs3cret',
  MASTER_PORT=33306,
  MASTER_LOG_FILE='replica2-bin.000001',
  MASTER_LOG_POS=3442,
  MASTER_CONNECT_RETRY=10;
CHANGE MASTER TO MASTER_USE_GTID = slave_pos;
START SLAVE;
SHOW SLAVE STATUS\G;
```

Verify that the following is "Yes":

` Slave_IO_Running: Yes 
Slave_SQL_Running: Yes`

### Secondary server (last step)

Start MariaDB command line client:

```
mysql -uroot -p
```

Do the following but replace the log file name and position with the ones from your notes, from the primary server:

```
RESET SLAVE;
CHANGE MASTER TO
  MASTER_HOST='localhost',
  MASTER_USER='tms_replication_user',
  MASTER_PASSWORD='bigs3cret',
  MASTER_PORT=33306,
  MASTER_LOG_FILE='master1-bin.000001',
  MASTER_LOG_POS=3442,
  MASTER_CONNECT_RETRY=10;
CHANGE MASTER TO MASTER_USE_GTID = slave_pos;
START SLAVE;
SHOW SLAVE STATUS\G;
```

Verify that the following is "Yes":

` Slave_IO_Running: Yes
Slave_SQL_Running: Yes`

### Troubleshooting

The replication is done using the MariaDB binary logging and when a change is registered, it informs the other server who implements the SQL-command. If the command fails (which can be seen using SHOW SLAVE STATUS\G; ) no further changes are replicated. The best thing is to resolv the cause of the SQL error. 

If you are sure that you can skip the SQL-statement causing the error, you can make the replica server to move one step forward in the log:

```
STOP SLAVE;
SET GLOBAL SQL_SLAVE_SKIP_COUNTER = 1; 
START SLAVE;
```

### Switching users from primary to secondary server

Change the hostname of your TMS, for example tms.mydomain.com to point to your secondary server using DNS or by overriding it by adding a line in /etc/hosts (Linux) or C:/Windows/System32/drivers/etc/hosts (in Windows you need to run notepad as administrator to be able to edit). Add a line (replacing 192.168.1.2 with your secondary server's IP-address):

`192.168.2.1 tms.mydomain.com`
