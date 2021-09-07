# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=unused-argument

from .providers.ExtensionProvider import ExtensionProvider
from .providers.FluxConfigurationProvider import FluxConfigurationProvider
from .providers.SourceControlConfigurationProvider import SourceControlConfigurationProvider
from . import consts


# Source Control Configuration Methods

def sourcecontrol_create(cmd, client, resource_group_name, cluster_name, name, repository_url, scope, cluster_type,
                         operator_instance_name=None, operator_namespace='default',
                         helm_operator_chart_version='1.2.0', operator_type='flux', operator_params='',
                         ssh_private_key='', ssh_private_key_file='', https_user='', https_key='',
                         ssh_known_hosts='', ssh_known_hosts_file='', enable_helm_operator=None,
                         helm_operator_params=''):
    provider = SourceControlConfigurationProvider(cmd)
    return provider.create(resource_group_name, cluster_name, name, repository_url, scope, cluster_type,
                           operator_instance_name, operator_namespace, helm_operator_chart_version, operator_type,
                           operator_params, ssh_private_key, ssh_private_key_file, https_user, https_key,
                           ssh_known_hosts, ssh_known_hosts_file, enable_helm_operator, helm_operator_params)

def sourcecontrol_show(cmd, client, resource_group_name, cluster_type, cluster_name, name):
    provider = SourceControlConfigurationProvider(cmd)
    return provider.show(resource_group_name, cluster_type, cluster_name, name)


def sourcecontrol_list(cmd, client, resource_group_name, cluster_type, cluster_name):
    provider = SourceControlConfigurationProvider(cmd)
    return provider.list(resource_group_name, cluster_type, cluster_name)


def sourcecontrol_delete(cmd, client, resource_group_name, cluster_type, cluster_name, name):
    provider = SourceControlConfigurationProvider(cmd)
    return provider.delete(resource_group_name, cluster_type, cluster_name, name)


# Flux Configuration Methods

def flux_config_show(cmd, client, resource_group_name, cluster_type, cluster_name, name):
    provider = FluxConfigurationProvider(cmd)
    return provider.show(resource_group_name, cluster_type, cluster_name, name)


def flux_config_list(cmd, client, resource_group_name, cluster_type, cluster_name):
    provider = FluxConfigurationProvider(cmd)
    return provider.list(resource_group_name, cluster_type, cluster_name)


# pylint: disable=too-many-locals
def flux_config_create(cmd, client, resource_group_name, cluster_type, cluster_name, name, url=None,
                       scope='cluster', namespace='default', kind=consts.GIT, timeout=None, sync_interval=None,
                       branch=None, tag=None, semver=None, commit=None, local_auth_ref=None, ssh_private_key=None,
                       ssh_private_key_file=None, https_user=None, https_key=None, known_hosts=None,
                       known_hosts_file=None, suspend=False, kustomization=None, no_wait=False):

    provider = FluxConfigurationProvider(cmd)
    return provider.create(resource_group_name, cluster_type, cluster_name, name, url, scope, namespace, kind,
                           timeout, sync_interval, branch, tag, semver, commit, local_auth_ref, ssh_private_key,
                           ssh_private_key_file, https_user, https_key, known_hosts, known_hosts_file, suspend,
                           kustomization, no_wait)


def flux_config_create_source(cmd, client, resource_group_name, cluster_type, cluster_name, name, url=None,
                              scope='cluster', namespace='default', kind=consts.GIT, timeout=None, sync_interval=None,
                              branch=None, tag=None, semver=None, commit=None, local_auth_ref=None,
                              ssh_private_key=None, ssh_private_key_file=None, https_user=None, https_key=None,
                              known_hosts=None, known_hosts_file=None):

    provider = FluxConfigurationProvider(cmd)
    return provider.create_source(resource_group_name, cluster_type, cluster_name, name, url, scope, namespace,
                                  kind, timeout, sync_interval, branch, tag, semver, commit, local_auth_ref,
                                  ssh_private_key, ssh_private_key_file, https_user, https_key, known_hosts,
                                  known_hosts_file)


def flux_config_create_kustomization(cmd, client, resource_group_name, cluster_type, cluster_name, name,
                                     kustomization_name, dependencies=None, timeout=None, sync_interval=None,
                                     retry_interval=None, path='', prune=False, validation='none', force=False):

    provider = FluxConfigurationProvider(cmd)
    return provider.create_kustomization(resource_group_name, cluster_type, cluster_name, name, kustomization_name,
                                         dependencies, timeout, sync_interval, retry_interval, path, prune,
                                         validation, force)


def flux_config_delete(cmd, client, resource_group_name, cluster_type, cluster_name, name, force=False, no_wait=False, yes=False):
    provider = FluxConfigurationProvider(cmd)
    return provider.delete(resource_group_name, cluster_type, cluster_name, name, force, no_wait, yes)


# Extension Methods

def extension_show(cmd, client, resource_group_name, cluster_type, cluster_name, name):
    provider = ExtensionProvider(cmd)
    return provider.show(resource_group_name, cluster_type, cluster_name, name)


def extension_list(cmd, client, resource_group_name, cluster_type, cluster_name):
    provider = ExtensionProvider(cmd)
    return provider.list(resource_group_name, cluster_type, cluster_name)


def extension_create(cmd, client, resource_group_name, cluster_type, cluster_name, name,
                     extension_type, scope=None, auto_upgrade_minor_version=None, release_train=None,
                     version=None, target_namespace=None, release_namespace=None, configuration_settings=None,
                     configuration_protected_settings=None, configuration_settings_file=None,
                     configuration_protected_settings_file=None, tags=None, no_wait=False):
    provider = ExtensionProvider(cmd)
    return provider.create(resource_group_name, cluster_type, cluster_name, name, extension_type, scope,
                           auto_upgrade_minor_version, release_train, version, target_namespace,
                           release_namespace, configuration_settings, configuration_protected_settings,
                           configuration_settings_file, configuration_protected_settings_file)


def extension_delete(cmd, client, resource_group_name, cluster_type, cluster_name, name, force=False, no_wait=False):
    provider = ExtensionProvider(cmd)
    return provider.delete(resource_group_name, cluster_type, cluster_name, name, force, no_wait)
