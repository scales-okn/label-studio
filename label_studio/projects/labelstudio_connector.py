import os
import sys
import json
from pathlib import Path

import pymongo
import requests
from dotenv import load_dotenv

VERSION = 'V0'

# For local testing not in docker container (otherwise will get env vars form docker)
ENV_PATH = Path(__file__).parent.resolve() / '.env'
load_env_success = load_dotenv(ENV_PATH)
print(ENV_PATH)
print('load_env_success:', load_env_success)

# Replace with whatever needed to get the connector in 
#sys.path.append( str(Path.cwd().parents[1]))
sys.path.append(str(Path(__file__).parent.resolve()))
from connector import SCALESMongo

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
        
def remap_annotation(anno):
    ''' Remap annotations'''
    
    kind = anno['result'][0]['type']
    
    if kind=='choices':
        labels = anno['result'][0]['value']['choices']
    
    elif kind=='labels':
        labels = [x['value'] for x in anno['result']]
    
    # Taxonomy might be useful for very specific hierarchy stuff, but not for now
    elif kind=='taxonomy':
        labels = [",".join(x) for x in anno['result']["taxonomy"]]
    
    return labels
        
    
def transform_annotations(tasks,project_id, project_group, all_task_data=True, task_data_keys=[], **proj_kwargs):
    '''
    Parse the data returned from the export endpoint
    
    Inputs:
        - tasks (list): list of dicts, response from the tasks endpoint
        - project_id (int): id of the project
        - project_group (int or str): id or name of the project group
        - all_task_data (bool): if True, returns all data in the data dictionary (metadata about the tag)
        - task_data_keys (list or tuple): a list of keys to grab from the tasks data (metadata supplied along with the data to be tagged)

    '''
    all_annos = []
    
    # Iterate over all tasks
    for task in tasks:
        
        # Iterate over annotations list, will be multiple if multiple taggers in same project
        for anno in task['annotations']:
            
            #Annotation may not have a result?
            if not len(anno['result']):
                continue
                
            obj = {
                'annotation_id': anno['id'],
                'annotator_id': anno['completed_by']['id'],
                'annotator_email': anno['completed_by']['email'],
                'annotation_id': anno['id'],
                'task_data': task['data'] if all_task_data else {k:v for k,v in task['data'].items() if k in ['text', *task_data_keys]},
                'labels': remap_annotation(anno),
                'created_at': anno['created_at'],
                'updated_at': anno['updated_at'],
                'project_id': project_id,
                'project_group': project_group,
                **proj_kwargs
            }

            all_annos.append(obj)
                
    return all_annos

def gen_scales_project_id(project_id, version=VERSION):
    ''' Generate a scales project id, built off of labstud project id '''
    return f"{project_id}_{version}"

def update_mongo_projects(headers, db=db, version=VERSION):
    ''' Export all project metadata to the annotations.projects collection '''
    
    project_metadata = get_all_projects(headers=headers, verbose=True)
    # Generate scales id
    for proj in project_metadata:
        proj['scales_id'] = gen_scales_project_id(proj['id'])
        
    jobs = [
        pymongo.UpdateOne(
            filter = {'scales_id': proj['scales_id']},
            update = {'$set': proj, '$currentDate':{'_updated':{'$type':'date'}}},
            upsert = True
        )
        for proj in project_metadata
    ]
    try:
        bulk_res = db['projects'].bulk_write(jobs, ordered=False)
        return bulk_res
    except pymongo.errors.BulkWriteError as bwe:
        print(bwe.details)


def get_project_labelset(project_id, db=db, version=VERSION):
    ''' 
    Get the full set of labels available for tagging on a project
    
    Inputs:
        - project_id (int): The id of the project
    '''
    
    # Go fetch from mongo
    scales_id = gen_scales_project_id(project_id, version=version)
    res = db.completed_annotations.find_one({'scales_id':scales_id}, {'parsed_label_config':1})
    
    # Assuming only one subkey, structure varies by config
    subkey = list(res['parsed_label_config'].keys())[0]
    
    return {k:v for k,v in res['parsed_label_config'][subkey].items() if k in ('type', 'labels')}
    
    
###
# Creating a sample
###
def create_sample(data_arr, sample_id, description, db=db, overwrite=False, **kwargs):
    '''
    Main sample creation function.
    
    Inputs:
        - data_arr(list of dicts): Must be a list of dicts like so: 
        [ {'data': {'text': 'sometext1'}}, {'data': {'text':'sometext2'}]
        The innermost dictionaries can have additional keys that will be passed through
        
        - sample_id (str): identifier/name for the sample
        - description (str): description of the sample
        - overwrite (bool): if False won't let you insert a sample if one with same sample_id already exists
        - **kwargs: passed in to the sample collection under the metadata key
    
    '''
    
    if not overwrite:
        samples = list_all_samples(db)
        if sample_id in (sample['sample_id'] for sample in samples):
            raise ValueError(f"Sample with name '{sample_id}' already exists. Choose a different name or use `overwrite`=True")
    
    
    # Validate data_arr
    for entry in data_arr:
        assert type(entry)==dict
        assert 'data' in entry
        assert type(entry['data'])==dict
        assert 'text' in entry['data']
        assert type(entry['data']['text'])==str
        
    assert type(sample_id)==str
    
    sample_collection = {
        'sample_id': sample_id,
        'description': description,
        'sample_arr': data_arr,
        'metadata': kwargs
    }
    
    return db.samples.insert_one(sample_collection)


def create_sample_from_cases(ucid2rows, sample_id, description, db=db, overwrite=False, **kwargs):
    '''
    Create a sample by specifying ucids and rows, pulls data from mongo cases collection
    
    Inputs:
        - ucid2rows (dict): dict with ucids as keys and iterable of docket row (ordinal) indexes to use in sample e.g. {'ucid1': [0,1,5], 'ucid2': [1], ...}
        * See create_sample for other args
    
    '''
    
    cases_collection = SM.connection['scales'].cases
    cases = cases_collection.find(
        filter = {'ucid': {'$in': list(ucid2rows.keys()) }},
        projection = {'ucid':1, 'docket':1}
    )
    
    data_arr = []
    for case in cases:
        
        entries = [
            {'data': 
                {
                    'ucid': case['ucid'],
                    'ord': ordinal,
                    'ind': case['docket'][ordinal]['ind'],
                    'text': case['docket'][ordinal]['docket_text']
                }
            }
        
            for ordinal in ucid2rows[case['ucid']]
        ]
        data_arr.extend(entries)
        
    return create_sample(data_arr, sample_id, description, db=db, overwrite=overwrite, **kwargs)

def create_sample_simple(str_arr, sample_id, description, db=db, overwrite=False, **kwargs):
    '''
    Create a simple sample from an array of strings
    
    Inputs:
        - str_arr (iterable of strings): an iterable of strings
        * See create_sample for other args
    '''
    data_arr = [
        {'data':{'text': x}}
        for x in str_arr
    ]
    
    return create_sample(data_arr, sample_id, description, db=db, overwrite=overwrite, **kwargs)

def gen_scales_annotation_id(anno_id, scales_project_id):
    return f"{anno_id}_{scales_project_id}"

def export_project_annotations(project_id, headers=headers, db=db, project_group=None, all_task_data=True, task_data_keys=[], **proj_kwargs):
    '''
    Export all annotations to Mongo for a given project
    '''
    
    scales_project_id = gen_scales_project_id(project_id)
    
    annos = get_project_annotations(project_id, headers=headers)
    transformed = transform_annotations(annos, project_id, project_group, all_task_data=True, task_data_keys=[], **proj_kwargs)
    
    for anno in transformed:
        anno['scales_annotation_id'] = gen_scales_annotation_id(anno['annotation_id'], scales_project_id)
    
    jobs = [
        pymongo.UpdateOne(
            filter = {'scales_annotation_id': anno['scales_annotation_id']},
            update = {'$set': anno, '$currentDate':{'_updated':{'$type':'date'}}},
            upsert = True
        )
        for anno in transformed
    ]
    
    try:
        bulk_res = db['completed_annotations'].bulk_write(jobs, ordered=False)
        return bulk_res
    except pymongo.errors.BulkWriteError as bwe:
        print(bwe.details)
        
        
def pull_annotations(project_ids, db=db):
    ''' 
    Pull clean annotations from Mongo 
    
    Inputs:
        - project_ids (list): a list of labelstudio project ids e.g [9,12]
    Output:
        (list) list of results from the annotations.completed_annotations collection
    '''
    res = db['completed_annotations'].find( {'project_id':{'$in':project_ids}} )
    return list(res)