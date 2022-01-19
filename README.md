
# Original Readme
This is a SCALES fork of label-studio that adds some additional functionality. For the original readme see [here](https://github.com/heartexlabs/label-studio#readme).
Note: this repo is **public** (forks stay public!)

# Docker app
The docker side of the Label-Studio repo has been adjusted so that the docker image will be built from scratch (i.e. using the changes this fork has made to the Django app which is in the [./label_studio]() directory) rather than pulling the image from Docker Hub. All of the changes are made in the [docker-compose](./docker-compose.yml) file.

The Docker app has the following containers:
- `app`: the container that (locally) builds and runs the label-studio django app
- `db`: a postgres database (running on 11.5).

*Note: This app doesn't use nginx, the official docker-compose.yml file wasn't working properly with the way nginx was setup at the time this was created (might have been fixed since!).*


## Setup
To use this app you need to have the following variables defined in a `.env` file in the root directory of this project.

### The `.env` file
Defines the following variables:

 - *LABEL_STUDIO_USERNAME*: the initial/admin username for Label Studio
 - *LABEL_STUDIO_PASSWORD*: the initial/admin password for Label Studio
 - *LABEL_STUDIO_PORT_EXT*: the port over which to expose the Label Studio app
 - *LABEL_STUDIO_TOKEN*: the token for the Label studio admin user (retrieved from the UI after initial build)
 - *POSTGRES_PASSWORD*:  the password for the `postgres` user in the database
 - *POSTGRES_PORT_EXT*:  the port to expose the Postgres server
 
### Mongo Credentials
You also need to put the mongo env file at `./label-studio/label_studio/projects/.mongo.env`. See instructions in the  [infrastructure_dev repo](https://github.com/scales-okn/infrastructure_dev/blob/master/code/db/mongo/README.md#steps) for what that should look like.

# Deploying
This app is deployed in a Digital Ocean droplet:
- Droplet name: scales-labelstudio
- IP address: XXXXXXXXX (see Digital Ocean)
- The `LABEL_STUDIO_PORT_EXT` env variable for the live version should be port 80.


## Accessing the container

### First time access
To access the droplet for the first time you need to post your ssh key into the `~/.ssh/authorized_keys` file, you can do this through the web console (finicky!) or  using the `ssh-copy-id` utility on your local machine:

```
ssh-copy-id -i <path_to_your_public_key> root@<droplet_IP_address>
```


### ssh'ing
Then you can connect with:
```bash
ssh root@<droplet_IP_address>
```
This repo is cloned on the droplet at this path: `~/label-studio`.  Once you have ssh'd in  you can do any docker stuff from that directory.

***The following assumes that you have `cd`'d into that directory:***

### To check the status:
```
docker-compose ps
```
### To get into the app container's terminal
```
docker-compose exec app bash
```

### Viewing live log output
```
docker-compose logs -f app
```


## Updating
To pull the latest version you can just do a `git pull` from inside of that directory (the ssh key of the droplet has been added to the GitHub deploy keys for this repo) so it will authenticate itself. Just pulling the repo will __not__ update the live server (as it needs to rebuild the django app). To do this you will need to do the following (after you have done a `git pull` from inside the repo inside the container):
```bash
docker-compose down
docker-compose build
docker-compose up -d #detaching from the session is vital
```
# Misc
## Adding 'Notes' section to labelling config
To add a notes section you can add a TextArea to the label config (basically copied from the 'Text Summarization' template). The two additional lines are

```xml
    <Header value="Notes"/>
    <TextArea name="notes" toName="text" showSubmitButton="true" maxSubmissions="1" editable="true"/>
```
- The `maxSubmisssions="1"` makes sure only one note can be added per task
- The `editable="true"` allows tagger to edit the note
- The `name="notes"` is the name you want to be the key for this data in the export
- The `toName="text"` not 100% on this, think it needs to be the same as the other component of the tagging (choice/ner etc.)
