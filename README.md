SAPI - SLURM REST API
=====================
sapi is a RESTful wrapper around the PySlurm interface utilizing Python Connexion. The goal of slurm-api is to provide a centralized interface for web applications, portals, and CLI utilities to interact with a site's scheduler instead of requiring each such instance to maintain the site's SLURM configuration files and correctly versioned packages.


sapi features
-------------
- Swagger UI for API
- Centralized interface for web applications and CLI tools to interface with SLURM
- Limits the spread and maintenance of SLURM configuration files, munge keys, and where root must be enabled to interact with the scheduler
- Built-in authenticaion methods or delegation via bearer auth


current slurm features
----------------------
Features are implemented to the extent required by our projects. If certain slurm interactively would help your site or product, please open a feature request or upvote if it already exists. 

- partitions 
  - (GET): utilizes the pyslurm/slurm source fields
- reservations
  - (GET): utilizes the pyslurm/slurm source fields
- nodes
  - (GET): utilizes the pyslurm/slurm source fields
- jobs
  - note: job interaction is limited to the user name encoded in the jwt token used to access sapi
  - (GET): utilizes the pyslurm/slurm source fields
  - (POST): external call out to sbatch - minimal fields set to date based on sbatch options
  - (DELETE): cancel a scheduled or running job


Prerequisites
=============
Python 3.6+ (other versions may work but have not been tested)

Example Development/Testing Environment:

```bash
$ pip list
Package                Version
---------------------- ---------
asn1crypto             0.24.0
certifi                2019.6.16
cffi                   1.12.3
chardet                3.0.4
Click                  7.0
clickclick             1.2.2
connexion              2.3.0
cryptography           2.7
Cython                 0.29.11
Flask                  1.1.0
Flask-Cors             3.0.8
idna                   2.8
inflection             0.3.1
itsdangerous           1.1.0
Jinja2                 2.10.1
jsonschema             2.6.0
MarkupSafe             1.1.1
openapi-spec-validator 0.2.7
pip                    10.0.1
pycparser              2.19
pyOpenSSL              19.0.0
pyslurm                18.8.4.1
PyYAML                 5.1.1
requests               2.22.0
setuptools             39.0.1
six                    1.12.0
swagger-ui-bundle      0.0.5
urllib3                1.25.3
Werkzeug               0.15.4
```

Quick Start
===========
* Identify service node to deploy service on. This node must have the SLURM configuration files in place for the underlying libraries to properly interact with the scheduler

* Clone slurm-api

```bash
$ cd /opt
$ git clone git@github.com:UFResearchComputing/slurm-api.git sapi 
```

* Install dependencies (use a python3 virtual env or system python3)

```bash
$ cd /opt/sapi
$ pip install dependencies.txt
```

Running:

```bash
$ /opt/sapi/bin/sapi
```

Some configuration may be required as documented below.

* The sapi will be accepting connections on the port defined in **SAPI_CONFIG** (see also configuration options)
 
* The swagger UI for the api should be available at http://example.com:9090/v1.0/ui/ (see also configuration options)


Configuration
=============
The Swagger UI URL is read from the swagger.yaml definition currently. As such, set url correctly in

```bash
$ grep url /etc/sapi/swagger.yaml
    - url: http://example.com:9090/v1.0
```

slurm-api reads a INI configuration file. By default this is expected to be located at

```bash
    /etc/sapi/sapi.conf
```

However, you may set **SAPI_CONFIG** to modify the path to the configuration file which can be helpful in running development versus production instances.

Example:
--------

* To run a development instance on port 9090 over HTTP

```bash
$ cat /opt/sapi/conf/sapi.conf.example
[api]
port=9090
host=0.0.0.0
debug=true

[ssl]
enable=false
cert=/etc/pki/tls/certs/example.com.crt
key=/etc/pki/tls/private/example.com.key

[logging]
path=/var/log/sapi.log

[auth]
jwt_issuer=sapi
jwt_secret=CHANGEME
jwt_lifetime=3600
jwt_algorithm=HS256


$ export SAPI_CONFIG=/opt/sapi/conf/sapi.conf.example
$ /opt/sapi/bin/sapi
```

* To run directly over HTTPS, set ssl enable=true

* Sites running in production should place behind apache, nginx, or similar


Token Management
================
A minimal administrative CLI interface is provided, sapadm, which can be used to generate tokens and inspect tokens generated. It utilizes the same SAPI_CONFIG as the API.

```bash
[admin@example sapi]# /opt/sapi/bin/sapiadm 
usage: sapiadm [-h] (-u USER | -t TOKEN) {create,view}
```

To generate a token:

```bash
[admin@example sapi]# /opt/sapi/bin/sapiadm create -u exampleUser
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzYXBpLnJjLnVmbC5lZHUiLCJpYXQiOjE1ODIxMTY0MzgsImV4cCI6MTYxMzY3MzM5MCwic3ViIjoiZXhhbXBsZVVzZXIifQ.arcSdErOsz5-b9tucH0VZKMYIWTZyuEHv0GmjDhVSN4
```

To inspect a token which has been generated by this program with the same signing authority and secret:

```bash
[root@sapi2 sapi]# /opt/sapi/bin/sapiadm view -t eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzYXBpLnJjLnVmbC5lZHUiLCJpYXQiOjE1ODIxMTY0MzgsImV4cCI6MTYxMzY3MzM5MCwic3ViIjoiZXhhbXBsZVVzZXIifQ.arcSdErOsz5-b9tucH0VZKMYIWTZyuEHv0GmjDhVSN4
User:     exampleUser
Issuer:   example.com
Created:  2020-01-19 07:47:18
Expires:  2021-01-18 13:36:30

```


Packaging
=========


FIXME


Documentation
=============
[GitHub Wiki](https://github.com/UFResearchComputing/slurm-api/wiki)

Changes
=======
[GitHub Releases](https://github.com/UFResearchComputing/slurm-api/releases)


Features and Bug Reporting
==========================
Bugs and feature requests can be filed at 

[GitHub Issues](https://github.com/UFResearchComputing/slurm-api/issues)

Licence
=======
Copyright 2020 UFIT Research Computing

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

