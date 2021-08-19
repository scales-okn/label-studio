# Original Readme
This is a fork of label-studio, see the original readme [here](https://github.com/heartexlabs/label-studio#readme)

# Docker app
The docker side of the Label-Studio repo has been adjusted so that the docker image will be built from scratch (i.e. using the changes this fork has made in the `label_studio` directory) rather than pulling the image from Docker Hub. All of the changes are made in the [docker-compose](./docker-compose.yml) file.

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
 
