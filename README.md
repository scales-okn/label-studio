# Original Readme
This is a fork of label-studio, see the original readme [here](https://github.com/heartexlabs/label-studio#readme)

# Docker app
The docker side of the Label-Studio repo has been adjusted so that the docker image will be built from scratch (i.e. using the changes this fork has made to the Django app which is in the [./label_studio]() directory) rather than pulling the image from Docker Hub. All of the changes are made in the [docker-compose](./docker-compose.yml) file.

The Docker app has the following containers:
- `app`: the latest Label Studio image
- `db`: a postgres database (running on 11.5).

*Note: This app doesn't use nginx, the official docker-compose.yml file wasn't working properly with the way nginx was setup at the time this was created (might have been fixed since).*


## Setup
To use this app you need to have the following variables defined in a `.env` file in the root directory of this project.

### The `.env` file
Defines the following variables:

 - *LABEL_STUDIO_USERNAME*: the initial/admin username for Label Studio
 - *LABEL_STUDIO_PASSWORD*: the initial/admin password for Label Studio
 - *LABEL_STUDIO_PORT_EXT*: the port to expose the Label Studio app
 - *POSTGRES_PASSWORD*:  the password for the `postgres` user in the database
 - *POSTGRES_PORT_EXT*:  the port to expose the Postgres app
 


# Deploying
This app is deployed in a Digital Ocean droplet:
- Droplet name: scales-labelstudio
- IP address: 134.209.74.60
- The `LABEL_STUDIO_PORT_EXT` env variable for the live version should be port 80.







## Accessing the container

### First time access
To access the droplet for the first time you need to post your ssh key into the `~/.ssh/authorized_keys` file, you can do this through the web console (finicky!) or have someone with access paste in for you.

### ssh'ing
Then you can connect with:
```bash
ssh root@134.209.74.60
```
This repo is cloned on the droplet = at `~/label-studio`.  Once you have ssh'd in  you can do any docker stuff from that directory the following assumes that you have `cd`'d into it. 

### To check the status:
```
docker-compose ps
```
### To get into the app container's terminal
```
docker-compose exec app bash
```


## Updating
To pull the latest version you can just do a `git pull` from inside of that directory (the ssh key of the droplet has been to the GitHub deploy keys for this repo) so it will authenticate itself. Just pulling the repo will __not__ update the live server (as it needs to rebuild the django app). To do this you will need to:
```bash
docker-compose down
docker-compose build
docker-compose up -d #detaching from the session is vital
```
