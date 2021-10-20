# PEERCTL

## Quickstart

To get a local repo and change into the directory:
```sh
git clone git@github.com:fullctl/peerctl
cd peerctl
```
Peerctl is containerized with Docker. First we want to copy the example environment file:
```sh
cp Ctl/dev/example.env Ctl/dev/.env
```
Any of the env variables can be changed, and you should set your own secret key. 

### Authentication and accounts

peerctl requires a fullctl aaactl instance to use as an authentication and account management service.

Please checkout and install https://github.com/fullctl/aaactl and once you have done so, set the following environment variables in your `.env` file

- OAUTH_TWENTYC_HOST: the url of your aaactl instance (e.g, https://localhost:8001)
- OAUTH_TWENTYC_KEY: the oauth application client id
- OAUTH_TWENTYC_SECRET: the oauth application client secret

- SERVICE_KEY: Internal API key (can be created/managed inside aaactl django admin)

Note you will need to give users permissions (in aaactl) to the following namespaces for peerctl to work correctly:

- `verified.asn.{asn}.fullctl` where {asn} should be the actual asn (e.g, 63311)

**note** - if authentication through peeringdb is provided in your aaactl instance asn verification can be done automatically by linking your peeringdb account to your aaactl account


- PDBCTL_HOST: pdbctl host address

### Building and starting

You can launch the app via: 
```sh
Ctl/dev/compose.sh build
Ctl/dev/compose.sh up
```

The first time you run `compose.sh up` it will create a folder `postgres_data` in the top-level `peerctl` directory which contains your Postgres data and will initialize the Postgres database with a user according to the settings you've provided. Generally, the compose script will automatically perform migrations within the Django app; however, the first time you run `compose.sh up` you may find that the Django app is unable to perform migrations because the Postgres database is still being initialized. To solve this, simply wait until the Postgres db is initialized, and then stop the Docker containers with

```sh
Ctl/dev/compose.sh down
```

On running `compose.sh up` any subsequent time, the Django app will be able to run migrations properly. Additionally, if you're starting up the app for the first time, you will want to `ssh` into the Django container and run a few additional commands. Do this **without** the services currently running, again stopping your containers with `compose.sh down` if necessary. `Ctl/dev/run.sh /bin/sh` will launch the services properly and ssh into the Django container for you:

```sh
Ctl/dev/run.sh createcachetable
```

### PeeringDB data

Peerctl uses data sourced from PeeringDB to inform its peer information.

This is however not directly done, but will instead use a [pdbctl](https://github.com/fullctl/pdbctl) instance.

Pdbctl allows us to provide one coherent snapshot of peeringdb data to use in all fullctl services.

Please refer to the pdbctl documentation on how to setup.

Your `PDBCTL_HOST` setting should be specified to the host address of your pdbctl instance.


## On env variables

The environment file you copied from `example.env` contains variables for configuring both the Django and Postgres services- if you change the database name, user, or password, you must ensure the values still match between the Django and Postgres settings. The Django database variables are passed directly into the Django application settings so all five `DATABASE_` settings should remain defined.

## API Key auth

### Method 1: HTTP Header

```
Authorization: bearer {key}
```

```
curl -X GET https://localhost/api/20c/ix/ -H "Authorization: bearer {key}"
```

### Method 2: URI parameter

```
?key={key}
```

## Generate openapi schema

```sh
python manage.py generateschema > django_peerctl/static/peerctl/openapi.yaml
cp django_peerctl/static/peerctl/openapi.yaml ../docs/openapi.yaml
```
