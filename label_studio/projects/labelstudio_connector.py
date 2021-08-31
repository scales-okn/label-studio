import os
import sys
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

# For local testing not in docker container (otherwise will get env vars form docker)
ENV_PATH = Path(__file__).resolve()/ '.env'
load_env_success = load_dotenv(ENV_PATH)
print('load_env_success:', load_env_success)

# Replace with whatever needed to get the connector in 
#sys.path.append( str(Path.cwd().parents[1]))
from .connector import SCALESMongo

# Mongo connection
SM = SCALESMongo(database='annotations', env_file='.env')
SM.connect()
db = SM.db

#Constants
host = os.environ['LABEL_STUDIO_HOST']
port = os.environ['LABEL_STUDIO_PORT_EXT']
base_url = f"http://{host}:{port}"
api_url = base_url + "/api"
proj_url = f"{api_url}/projects"
headers = {'Authorization': f"Token {os.environ.get('LABEL_STUDIO_TOKEN')}" }

# Keys to copy when duplicating a project (subset of what's returned by the API because only some can be used in initialisation)
COPY_KEYS = [ 
    'description',
    'label_config',
    'expert_instruction',
    'show_instruction',
    'show_skip_button',
    'enable_empty_annotation',
    'show_annotation_history',
    'organization',
    'color',
    'maximum_annotations',
    'is_published',
    'model_version',
    'is_draft',
    'created_by',
    'min_annotations_to_start_training',
    'show_collab_predictions',
    'sampling',
    'show_ground_truth_first',
    'show_overlap_first',
    'overlap_cohort_percentage',
    'task_data_login',
    'task_data_password',
    #  'control_weights', # Causing trouble
    'evaluate_predictions_automatically'
    ]


###
# Getters
###

def get_all_projects(headers=headers, verbose=False):
    brief_keys = ('id', 'title', 'description', 'group', 'task_number')
    res = requests.get(f"{proj_url}/all", headers=headers)
    all_projects = res.json()
    if verbose:
        return all_projects
    else:
        return [{k:v for k,v in proj.items() if k in brief_keys} for proj in all_projects]

def get_all_tasks_by_project(proj_id, headers=headers):
    ''' Get all the tasks for a project
    
    Inputs:
        - proj_id (int or str): the internal label-studio project id
        - headers (dict): headers to use in the request (expects 'Authorization' key and value to authenticate)
    Outputs:
        (list) list with a dict for each task
    '''
    url_project_tasks = f"{proj_url}/{proj_id}/tasks"
    params = {'page_size':-1}
    res = requests.get(url_project_tasks, headers=headers, params=params)
    if res.ok:
        return res.json()
    else:
        raise ValueError(repr_error(res))
        
        
### 
# Import side
###

def create_project(title, label_config=None, headers=headers, prevent_title_duplication=True, **data_kwargs):
    '''
    Create a label-studio project. 
    Many many options... see https://labelstud.io/api#operation/api_projects_create
    Inputs:
        - title (str): project title
        - label_config (str): label config in XML format
        - headers (dict): headers to send with request
        - prevent_name_duplicate (bool): if True, prevents a project with the same name from being created
        - data_kwargs (dict): additional arguments to pass in request data, see labelstudio API for full list
        
    Output:
        (dict) the api response (includes full project settings, notably including the new project id
    '''
    
    if prevent_title_duplication:
        all_projects = get_all_projects(headers=headers, verbose=False)
        print(all_projects)
        if any(proj['title']==title for proj in all_projects):
            raise ValueError(f"Title Duplication: Project with title '{title}' already exists, (set `prevent_title_duplication` to False to override)")
        
    
    data = {'title': title, 'label_config':label_config, **data_kwargs}
    
    resp = requests.post(proj_url, data=data, headers=headers )
    if not resp.ok:
        raise ValueError( repr_error(resp) )
    else:
        return resp.json()
    
def duplicate_project(proj_id, new_title, headers=headers, prevent_title_duplication=True, settings_only=True):
    '''
    Duplicate a label studio project
    
    Inputs:
        - proj_id (int): id of the project you want to copy
        - new_title (str): title of the new project
        - headers (dict): headers to use in the queries
        - prevent_title_duplication (bool):
        - settings_only (bool) : if True only copies settings, otherwise copies the tasks over also
    Output:
        (dict) the return of the /projects/ api when new project is created. Notably it includes the id of the new project
    '''
    
    # Step 1: Get data on the project to be duplicated
    url = f"{api_url}/projects/{proj_id}/"
    resp1 = requests.get(url, headers=headers)
    print(headers)
    print(resp1)
    print(resp1.content)
    
    if not resp1.ok:
        raise ValueError( repr_error(resp1) )
    
    new_data = {k:v for k,v in resp1.json().items() if k in COPY_KEYS}
    
    # jsonify: to get around some encoding issues
    new_data = json.loads(json.dumps(new_data))
    print(new_data)
    
    # Step 2: Create new project with the same settings
    new_project_data = create_project(new_title, headers=headers, 
                                      prevent_title_duplication=prevent_title_duplication, **new_data)
        
    if not settings_only:
        
        # Step 3: Get tasks from the initial project

        tasks = get_all_tasks_by_project(proj_id, headers=headers)

        # Step 4: import tasks into new project
        # Just use the body of the tasks (not the metadata that relates to the original project)
        body = [t['data'] for t in tasks]
        tasks = import_tasks(new_project_data['id'], body=body, headers = headers)

    return new_project_data
    
    
def import_tasks(project_id, body, headers=headers):
    ''' 
    Import tasks into a specific project
    
    Inputs:
        - project_id (int): the project id
        - body (list): list of tasks, each a dict, structure depends on the labelling setup (but generally includes 'text' key)
        - headers (dict): request headers
    Output:
        (dict) the response from the import API (lists task_count etc.)
    '''
    url = f"{api_url}/projects/{project_id}/import"
    headers = {'Content-Type': 'application/json', **headers}

    resp = requests.post(url, json=body, headers=headers)

    if resp.ok:
        return resp.json()
    else:
        raise ValueError( repr_error(resp) )
        
        
def import_tasks_from_mongo(sample_id, proj_id, db=db, headers=headers):
    
    sample = db.samples.find_one({'sample_id': sample_id})
    return import_tasks(proj_id, body=sample['sample_arr'], headers=headers)

def list_all_samples(db=db):
    ''' List all of the data samples in mongo annotations.samples'''
    return list(db.samples.find({}, {'sample_id':1, 'description':1}))



###
# Export Side
###

def get_project_annotations(proj_id, headers=headers):
    ''' Get all tasks and their annotations for a project, skipping tasks that don't have annotations  '''
    resp = requests.get(f"{proj_url}/{proj_id}/export", params={'exportType':'JSON'}, headers=headers)
    
    if resp.ok:
        return resp.json()
    else:
        raise ValueError( repr_error(resp) )
        
def remap_annotation(value, kind):
    ''' Remap annotations'''
    
    if kind=='choices':
        labels = value['choices']
        return labels
    
    elif kind=='labels':
        # Structured well already: includes keys ('start', 'end', 'text', 'labels')
        if len(value['labels']) > 1:
            raise ValueError("Don't know how to handle ner with multiple labels applied to same label-studio-annotation")
        else:
            value['label'] = value['labels'][0]
            del value['labels']
        return value
    
    # Taxonomy might be useful for very specific hierarchy stuff, but not for now
    elif kind=='taxonomy':
        labels = [",".join(x) for x in value["taxonomy"]]
        return labels
    
    
def transform_tasks(tasks, project_id, task_data_keys=[], all_task_data=False):
    '''
    Parse the data returned from the tasks endpoint
    
    Inputs:
        - tasks (list): list of dicts, response from the tasks endpoint
        - task_data_keys (list or tuple): a list of keys to grab from the tasks data (metadata supplied along with the data to be tagged)
        - all_task_data (bool): if True, returns all data in the data dictionary (metadata about the tag)
    '''
    all_annos = []
    
    # Iterate over all tasks
    for task in tasks:
        
        # Iterate over annotations list, will be multiple if multiple taggers in same project
        for anno in task['annotations']:
            
            #Annotation may not have a result?
            if not len(anno['result']):
                continue
                
            # Will usually be a singleton list I think??
            for res in anno['result']:
                obj = {
                    'annotator_id': anno['completed_by']['id'],
                    'annotator_email': anno['completed_by']['email'],
                    'task_data': {k:v for k,v in task['data'].items() if (k in task_data_keys) or all_task_data },
                    'labels': remap_annotation(res['value'], kind=res['type']),
                    'project_id': project_id,
                    'created_at': anno['created_at'],
                    'updated_at': anno['updated_at']
                }
                
                all_annos.append(obj)
                
    return all_annos








        
