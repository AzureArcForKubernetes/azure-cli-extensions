# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core import AzCommandsLoader

from azext_k8s_configuration._help import helps  # pylint: disable=unused-import


class k8s_configCommandsLoader(AzCommandsLoader):

    def __init__(self, cli_ctx=None):
        from azure.cli.core.commands import CliCommandType
        from azext_k8s_configuration._client_factory import k8s_configuration_client
        k8s_config_custom = CliCommandType(
            operations_tmpl='azext_k8s_configuration.custom#{}',
            client_factory=k8s_configuration_client)
        super().__init__(cli_ctx=cli_ctx,
                         custom_command_type=k8s_config_custom)

    def load_command_table(self, args):
        from azext_k8s_configuration.commands import load_command_table
        load_command_table(self, args)
        return self.command_table

    def load_arguments(self, command):
        from azext_k8s_configuration._params import load_arguments
        load_arguments(self, command)


COMMAND_LOADER_CLS = k8s_configCommandsLoader
