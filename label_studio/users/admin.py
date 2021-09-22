"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
from django.contrib import admin
from django.apps import apps
from django.contrib.auth.admin import UserAdmin
from django.conf import settings
from django.contrib.auth.models import Group

from users.models import User
from projects.models import Project, ProjectGroup, UserGroup
from ml.models import MLBackend, MLBackendTrainJob
from tasks.models import Task, Annotation
from organizations.models import Organization


class UserAdminShort(UserAdmin):

    def __init__(self, *args, **kwargs):
        super(UserAdminShort, self).__init__(*args, **kwargs)

        # we have empty username - remove it to escape confuse about empty fields in admin web
        self.list_display = [l for l in self.list_display if l != 'username']

        self.fieldsets = ((None, {'fields': ('password', )}),
                          ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
                          ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',)}),
                          ('Important dates', {'fields': ('last_login', 'date_joined')}))
        


models = apps.get_models()

for model in models:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass

