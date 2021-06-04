# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=unused-argument

from azure.cli.core.azclierror import InvalidArgumentValueError, RequiredArgumentMissingError
from knack.log import get_logger

from .PartnerExtensionModel import PartnerExtensionModel

from msrestazure.azure_exceptions import CloudError

from azure.cli.core.commands.client_factory import get_subscription_id

from pyhelm.chartbuilder import ChartBuilder
from packaging import version
import yaml

from azext_k8s_extension.partner_extensions.PartnerExtensionModel import PartnerExtensionModel
from azext_k8s_extension.partner_extensions.ContainerInsights import _get_container_insights_settings

from .._client_factory import cf_resources

from ..vendored_sdks.models import ExtensionInstance
from ..vendored_sdks.models import ExtensionInstanceUpdate
from ..vendored_sdks.models import ScopeCluster
from ..vendored_sdks.models import Scope

logger = get_logger(__name__)


class OpenServiceMesh(PartnerExtensionModel):
    def Create(self, cmd, client, resource_group_name, cluster_name, name, cluster_type, extension_type,
               scope, auto_upgrade_minor_version, release_train, version, target_namespace,
               release_namespace, configuration_settings, configuration_protected_settings,
               configuration_settings_file, configuration_protected_settings_file):

        """ExtensionType 'microsoft.openservicemesh' specific validations & defaults for Create
           Must create and return a valid 'ExtensionInstance' object.

        """
        # NOTE-1: Replace default scope creation with your customization, if required
        # Scope must always be cluster
        ext_scope = None
        if scope == 'namespace':
            raise InvalidArgumentValueError("Invalid scope '{}'.  This extension can be installed "
                                            "only at 'cluster' scope.".format(scope))

        scope_cluster = ScopeCluster(release_namespace=release_namespace)
        ext_scope = Scope(cluster=scope_cluster, namespace=None)

        valid_release_trains = ['staging', 'pilot']
        # If release-train is not input, set it to 'stable'
        if release_train is None:
            raise RequiredArgumentMissingError(
                "A release-train must be provided.  Valid values are 'staging', 'pilot'."
            )

        if release_train.lower() in valid_release_trains:
            # version is a mandatory if release-train is staging or pilot
            if version is None:
                raise RequiredArgumentMissingError(
                    "A version must be provided for release-train {}.".format(release_train)
                )
            # If the release-train is 'staging' or 'pilot' then auto-upgrade-minor-version MUST be set to False
            if auto_upgrade_minor_version or auto_upgrade_minor_version is None:
                auto_upgrade_minor_version = False
                logger.warning("Setting auto-upgrade-minor-version to False since release-train is '%s'", release_train)
        else:
            raise InvalidArgumentValueError(
                "Invalid release-train '{}'.  Valid values are 'staging', 'pilot'.".format(release_train)
            )

        # NOTE-2: Return a valid ExtensionInstance object, Instance name and flag for Identity
        create_identity = False

        _validate_tested_distro(cmd, resource_group_name, cluster_name, version)

        extension_instance = ExtensionInstance(
            extension_type=extension_type,
            auto_upgrade_minor_version=auto_upgrade_minor_version,
            release_train=release_train,
            version=version,
            scope=ext_scope,
            configuration_settings=configuration_settings,
            configuration_protected_settings=configuration_protected_settings,
            identity=None,
            location=""
        )
        return extension_instance, name, create_identity

    def Update(self, extension, auto_upgrade_minor_version, release_train, version):
        """ExtensionType 'microsoft.openservicemesh' specific validations & defaults for Update
           Must create and return a valid 'ExtensionInstanceUpdate' object.

        """
        #  auto-upgrade-minor-version MUST be set to False if release_train is staging or pilot
        if release_train.lower() in ['staging', 'pilot']:
            if auto_upgrade_minor_version or auto_upgrade_minor_version is None:
                auto_upgrade_minor_version = False
                # Set version to None to always get the latest version - user cannot override
                version = None
                logger.warning("Setting auto-upgrade-minor-version to False since release-train is '%s'", release_train)

        return ExtensionInstanceUpdate(
            auto_upgrade_minor_version=auto_upgrade_minor_version,
            release_train=release_train,
            version=version
        )


def _validate_tested_distro(cmd, cluster_resource_group_name, cluster_name, extension_version):

    if version.parse(str(extension_version)) <= version.parse("0.8.3"):
        logger.warning(f'\"testedDistros\" field unavailable for version {extension_version} of osm-arc, '
            'cannot determine if this kubernetes distribution has been tested for osm-arc')
        return

    subscription_id = get_subscription_id(cmd.cli_ctx)
    resources = cf_resources(cmd.cli_ctx, subscription_id)

    cluster_resource_id = '/subscriptions/{0}/resourceGroups/{1}/providers/Microsoft.Kubernetes' \
        '/connectedClusters/{2}'.format(subscription_id, cluster_resource_group_name, cluster_name)
    try:
        resource = resources.get_by_id(cluster_resource_id, '2020-01-01-preview')
        cluster_distro = resource.properties['distribution'].lower()
    except CloudError as ex:
        raise ex

    if cluster_distro == "general":
        logger.warning('kubernetes distribution is \"general\", cannot determine if this kubernetes '
            'distribution has been tested for osm-arc')
        return

    tested_distros = _get_tested_distros(extension_version)

    if tested_distros is None:
        logger.warning(f'\"testedDistros\" field unavailable for version {extension_version} of osm-arc, '
            'cannot determine if this kubernetes distribution has been tested for osm-arc')
    elif cluster_distro in tested_distros.split():
        logger.warning(f'{cluster_distro} is a tested kubernetes distribution for osm-arc')
    else:
        logger.warning(f'{cluster_distro} is not a tested kubernetes distribution for osm-arc')


def _get_tested_distros(version):

    chart_arc = ChartBuilder({
        "name": "osm-arc",
        "version": str(version),
        "source": {
            "type": "repo",
            "location": "https://azure.github.io/osm-azure"
        }
    })
    values = chart_arc.get_values()
    values_yaml = yaml.load(values.raw, Loader=yaml.FullLoader)

    try:
        return values_yaml['OpenServiceMesh']['testedDistros']
    except KeyError:
        return None
