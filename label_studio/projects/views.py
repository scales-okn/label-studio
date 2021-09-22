"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import json
import logging
import lxml.etree
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.exceptions import ValidationError
from projects.models import Project, ProjectGroup, UserGroup

from core.utils.common import get_object_with_check_and_log
from core.label_config import get_sample_task
from core.utils.common import get_organization_from_request

from organizations.models import Organization

from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict

from .labelstudio_connector import list_all_samples, import_tasks_from_mongo, export_project_annotations, duplicate_project
logger = logging.getLogger(__name__)


def project_manage(request):
    if not request.user.is_staff:
        return redirect('projects:project-index')

    print(request.POST)
    #ProjectSample.objects.all().delete()

    if 'remove_staff' in request.POST:
        user = get_user_model().objects.get(id=request.POST['remove_staff'])
        user.is_staff = False
        user.save()

    if 'add_staff' in request.POST:
        user = get_user_model().objects.get(id=request.POST['add_staff_id'])
        user.is_staff = True
        user.save()

    if 'add_user_group' in request.POST:
        user_group = UserGroup(name=request.POST['add_user_group_name'])
        user_group.save()

    if 'add_user_to_group' in request.POST:
        user_group = UserGroup.objects.get(id=request.POST['add_user_to_group_group'])
        user = get_user_model().objects.get(id=request.POST['add_user_to_group_user'])
        user_group.users.add(user)
        user_group.save()

    if 'remove_user_from_group' in request.POST:
        user_id, user_group_id = request.POST['remove_user_from_group'].split('-')
        user_group = UserGroup.objects.get(id=user_group_id)
        user = get_user_model().objects.get(id=user_id)
        user_group.users.remove(user)
        user_group.save()

    if 'create_project_group' in request.POST:
        try:
            if request.POST['create_project_group_template']:
                template = Project.objects.get(id=request.POST['create_project_group_template'])
                project_group = ProjectGroup(
                    name=request.POST['create_project_group_name'],
                    template=template,
                )
                project_group.save()
        except Exception as e:
            print(e)

    if 'create_project' in request.POST:
        project_group = ProjectGroup.objects.get(id=request.POST['create_project_project_group'])
        sample = request.POST['create_project_sample']
        project = duplicate_project(project_group.template.id, request.POST['create_project_name'])
        project = Project.objects.get(id=project['id'])
        import_tasks_from_mongo(sample, project.id)
        project.group = project_group
        project.sample = sample
        project.save()


    if 'backup_project' in request.POST:
        project = Project.objects.get(id=request.POST['backup_project'])
        export_project_annotations(project.id, project_group=project.group.name)

    if 'sync_samples' in request.POST:
        samples = [x['sample_id'] for x in list_all_samples()]
        existing_sample_ids = [x['name'] for x in ProjectSample.objects.values('name')]
        for sample_id in [x for x in sample_ids if x not in existing_sample_ids]:
            sample = ProjectSample(name=sample_id)
            sample.save()

    if 'remove_from_project' in request.POST:
        remove_type, remove_id, project_id = request.POST['remove_from_project'].split('-')
        project = Project.objects.get(id=project_id)
        if remove_type == 'group':
            user_group = UserGroup.objects.get(id=remove_id)
            project.user_groups.remove(user_group)
        elif remove_type == 'user':
            user = get_user_model().objects.get(id=remove_id)
            project.users.remove(user)
        project.save()
    else:
        if 'add_to_project' in request.POST:
            for info in request.POST.getlist('add_to_project'):
                try:
                    add_type, add_id, project_id = info.split('-')
                    project = Project.objects.get(id=project_id)
                    if add_type == 'group':
                        user_group = UserGroup.objects.get(id=add_id)
                        project.user_groups.add(user_group)
                    elif add_type == 'user':
                        user = get_user_model().objects.get(id=add_id)
                        project.users.add(user)
                    project.save()
                except Exception as e:
                    print(e)



    projects = Project.objects.all()

    grouped_projects = {}
    for project in projects:
        if not project.is_template:
            grouped_projects[project.group] = grouped_projects.get(project.group, []) + [project]

    users = get_user_model().objects.all()
    user_groups = [model_to_dict(x) for x in UserGroup.objects.all()]

    return render(request, 'projects/manage.html', {
        'users': users,
        'user_groups': user_groups,
        'projects': projects,
        'project_groups': ProjectGroup.objects.all(),
        'samples': [x['sample_id'] for x in list_all_samples()],
        'grouped_projects': grouped_projects,
    })

@login_required
def project_list(request):
    return render(request, 'projects/list.html')


@login_required
def project_settings(request, pk, sub_path):
    return render(request, 'projects/settings.html')


def playground_replacements(request, task_data):
    if request.GET.get('playground', '0') == '1':
        for key in task_data:
            if "/samples/time-series.csv" in task_data[key]:
                task_data[key] = "https://app.heartex.ai" + task_data[key]
    return task_data


@require_http_methods(['GET', 'POST'])
def upload_example_using_config(request):
    """ Generate upload data example by config only
    """
    config = request.GET.get('label_config', '')
    if not config:
        config = request.POST.get('label_config', '')

    org_pk = get_organization_from_request(request)
    secure_mode = False
    if org_pk is not None:
        org = get_object_with_check_and_log(request, Organization, pk=org_pk)
        secure_mode = org.secure_mode

    try:
        Project.validate_label_config(config)
        task_data, _, _ = get_sample_task(config, secure_mode)
        task_data = playground_replacements(request, task_data)
    except (ValueError, ValidationError, lxml.etree.Error):
        response = HttpResponse('error while example generating', status=status.HTTP_400_BAD_REQUEST)
    else:
        response = HttpResponse(json.dumps(task_data))
    return response
