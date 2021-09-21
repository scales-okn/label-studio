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
    res = db.projects.find_one({'scales_id':scales_id}, {'parsed_label_config':1})
    
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
