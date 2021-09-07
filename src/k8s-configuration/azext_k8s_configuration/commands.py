# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long
from azure.cli.core.commands import CliCommandType
from azext_k8s_configuration._client_factory import (
    k8s_configuration_fluxconfig_client,
    k8s_configuration_sourcecontrol_client
)
from .format import (
    fluxconfig_list_table_format,
    fluxconfig_show_table_format,
    sourcecontrol_list_table_format,
    sourcecontrol_show_table_format
)


def load_command_table(self, _):
    k8s_configuration_fluxconfig_sdk = CliCommandType(
        operations_tmpl='azext_k8s_configuration.vendored_sdks.operations#FluxConfigurationsOperations.{}',
        client_factory=k8s_configuration_fluxconfig_client
    )

    k8s_configuration_sourcecontrol_sdk = CliCommandType(
        operations_tmpl='azext_k8s_configuration.vendored_sdks.operations#SourceControlConfigurationsOperations.{}',
        client_factory=k8s_configuration_sourcecontrol_client
    )

    with self.command_group('k8s-configuration flux', k8s_configuration_fluxconfig_sdk, client_factory=k8s_configuration_fluxconfig_sdk, is_experimental=True) as g:
        g.custom_command('create', 'flux_config_create', supports_no_wait=True)
        g.custom_command('list', "flux_config_list", table_transformer=fluxconfig_list_table_format)
        g.custom_show_command('show', 'flux_config_show', table_transformer=fluxconfig_show_table_format)
        g.custom_command('delete', 'flux_config_delete', confirmation=True, supports_no_wait=True)
        # g.custom_command('source create', 'flux_config_create_source', supports_local_cache=True)
        # g.custom_command('kustomization create', 'flux_config_create_kustomization', supports_local_cache=True)

    with self.command_group('k8s-configuration', k8s_configuration_sourcecontrol_sdk, client_factory=k8s_configuration_sourcecontrol_sdk) as g:
        g.custom_command('create', 'sourcecontrol_create', deprecate_info=self.deprecate(redirect='k8s-configuration flux create'))
        g.custom_command('list', 'sourcecontrol_list', table_transformer=sourcecontrol_list_table_format, deprecate_info=self.deprecate(redirect='k8s-configuration flux list'))
        g.custom_show_command('show', 'sourcecontrol_show', table_transformer=sourcecontrol_show_table_format, deprecate_info=self.deprecate(redirect='k8s-configuration flux show'))
        g.custom_command('delete', 'sourcecontrol_delete', confirmation=True, deprecate_info=self.deprecate(redirect='k8s-configuration flux delete'))
