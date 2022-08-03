# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=unused-argument

from knack.log import get_logger

from ..vendored_sdks.models import Extension
from ..vendored_sdks.models import ScopeCluster
from ..vendored_sdks.models import Scope

from azure.cli.core.commands.client_factory import get_subscription_id
from .._client_factory import cf_resources

from .DefaultExtension import DefaultExtension
from .ContainerInsights import _get_container_insights_settings

logger = get_logger(__name__)


class AzureDefender(DefaultExtension):
    def Create(self, cmd, client, resource_group_name, cluster_name, name, cluster_type, extension_type,
               scope, auto_upgrade_minor_version, release_train, version, target_namespace,
               release_namespace, configuration_settings, configuration_protected_settings,
               configuration_settings_file, configuration_protected_settings_file):

        """ExtensionType 'microsoft.azuredefender.kubernetes' specific validations & defaults for Create
           Must create and return a valid 'Extension' object.

        """
        # NOTE-1: Replace default scope creation with your customization!
        ext_scope = None
        # Hardcoding  name, release_namespace and scope since ci only supports one instance and cluster scope
        # and platform doesn't have support yet extension specific constraints like this
        name = extension_type.lower()
        
        logger.warning('Ignoring name, release-namespace and scope parameters since %s '
                       'only supports cluster scope and single instance of this extension.', extension_type)
        release_namespace = self._choose_the_right_namespace(cmd, resource_group_name, cluster_name, name)
        logger.warning("Defaulting to extension name '%s' and using release-namespace '%s'", name, release_namespace)
        
        # Scope is always cluster
        scope_cluster = ScopeCluster(release_namespace=release_namespace)
        ext_scope = Scope(cluster=scope_cluster, namespace=None)
        is_ci_extension_type = False

        _get_container_insights_settings(cmd, resource_group_name, cluster_name, configuration_settings,
                                         configuration_protected_settings, is_ci_extension_type)

        # NOTE-2: Return a valid Extension object, Instance name and flag for Identity
        create_identity = True
        extension_instance = Extension(
            extension_type=extension_type,
            auto_upgrade_minor_version=auto_upgrade_minor_version,
            release_train=release_train,
            version=version,
            scope=ext_scope,
            configuration_settings=configuration_settings,
            configuration_protected_settings=configuration_protected_settings
        )
        return extension_instance, name, create_identity

    def _choose_the_right_namespace(self, cmd, cluster_resource_group_name, cluster_name, extension_name):
        logger.warning("Choosing the right namespace ...")

        subscription_id = get_subscription_id(cmd.cli_ctx)
        resources = cf_resources(cmd.cli_ctx, subscription_id)

        cluster_resource_id = '/subscriptions/{0}/resourceGroups/{1}/providers/Microsoft.Kubernetes' \
            '/connectedClusters/{2}/providers/Microsoft.KubernetesConfiguration/extensions/microsoft.azuredefender.kubernetes'.format(subscription_id, cluster_resource_group_name, cluster_name)
        resource = None
        try:
            resource = resources.get_by_id(cluster_resource_id, '2022-03-01')
        except:
            choosen_namespace = "mdc"
            logger.info("Defaulted to {0}...".format(choosen_namespace))
            return choosen_namespace

        choosen_namespace = resource.properties["scope"]["cluster"]["releaseNamespace"]
        logger.info("found an existing extension, using its namespace: {0}".format(choosen_namespace))
        return choosen_namespace
