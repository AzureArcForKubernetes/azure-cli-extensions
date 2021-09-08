# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=unused-argument

import os

from azure.cli.core.azclierror import DeploymentError, ResourceNotFoundError
from azure.cli.core.commands import cached_get, cached_put, upsert_to_collection, get_property
from azure.cli.core.util import sdk_no_wait, user_confirmation
from azure.cli.core.commands.client_factory import get_subscription_id

from azure.core.exceptions import HttpResponseError
from knack.log import get_logger

from ..confirm import user_confirmation_factory
from .._client_factory import (
    cf_resources,
    k8s_configuration_fluxconfig_client,
    k8s_configuration_extension_client
)
from ..utils import (
    get_parent_api_version,
    get_cluster_rp,
    get_data_from_key_or_file,
    get_duration,
    has_prune_enabled,
    to_base64,
    is_dogfood_cluster
)
from ..validators import (
    validate_cc_registration,
    validate_known_hosts,
    validate_repository_ref,
    validate_duration,
    validate_git_repository,
    validate_kustomization_list,
    validate_private_key,
    validate_url_with_params
)
from .. import consts
from ..vendored_sdks.v2021_06_01_preview.models import (
    FluxConfiguration,
    GitRepositoryDefinition,
    RepositoryRefDefinition,
    KustomizationDefinition,
)
from ..vendored_sdks.v2021_05_01_preview.models import (
    Extension,
    Identity
)
from .SourceControlConfigurationProvider import SourceControlConfigurationProvider

logger = get_logger(__name__)


class FluxConfigurationProvider:
    def __init__(self, cmd):
        self.extension_client = k8s_configuration_extension_client(cmd.cli_ctx)
        self.source_control_configuration_provider = SourceControlConfigurationProvider(cmd)
        self.cmd = cmd
        self.client = k8s_configuration_fluxconfig_client(cmd.cli_ctx)

    def show(self, resource_group_name, cluster_type, cluster_name, name):
        """Get an existing Kubernetes Source Control Configuration.

        """
        # Determine ClusterRP
        cluster_rp = get_cluster_rp(cluster_type)
        try:
            config = self.client.get(resource_group_name, cluster_rp, cluster_type, cluster_name, name)
            return config
        except HttpResponseError as ex:
            # Customize the error message for resources not found
            if ex.response.status_code == 404:
                # If Cluster not found
                if ex.message.__contains__("(ResourceNotFound)"):
                    message = ex.message
                    recommendation = 'Verify that the --cluster-type is correct and the Resource ' \
                                     '{0}/{1}/{2} exists'.format(cluster_rp, cluster_type, cluster_name)
                # If Configuration not found
                elif ex.message.__contains__("Operation returned an invalid status code 'Not Found'"):
                    message = '(FluxConfigurationNotFound) The Resource {0}/{1}/{2}/' \
                              'Microsoft.KubernetesConfiguration/fluxConfigurations/{3} ' \
                              'could not be found!' \
                              .format(cluster_rp, cluster_type, cluster_name, name)
                    recommendation = 'Verify that the Resource {0}/{1}/{2}/Microsoft.KubernetesConfiguration' \
                                     '/fluxConfigurations/{3} exists'.format(cluster_rp, cluster_type,
                                                                             cluster_name, name)
                else:
                    message = ex.message
                    recommendation = ''
                raise ResourceNotFoundError(message, recommendation) from ex
            raise ex

    def list(self, resource_group_name, cluster_type, cluster_name):
        cluster_rp = get_cluster_rp(cluster_type)
        return self.client.list(resource_group_name, cluster_rp, cluster_type, cluster_name)

    # pylint: disable=too-many-locals
    def create(self, resource_group_name, cluster_type, cluster_name, name, url=None, scope='cluster',
               namespace='default', kind=consts.GIT, timeout=None, sync_interval=None, branch=None,
               tag=None, semver=None, commit=None, local_auth_ref=None, ssh_private_key=None,
               ssh_private_key_file=None, https_user=None, https_key=None, known_hosts=None,
               known_hosts_file=None, suspend=False, kustomization=None, no_wait=False):

        # Determine the cluster RP
        cluster_rp = get_cluster_rp(cluster_type)
        dp_source_kind = ""
        git_repository = None

        # Validate and Create the Data before checking the cluster compataibility
        if kind == consts.GIT:
            dp_source_kind = consts.GIT_REPOSITORY
            git_repository = self._validate_and_get_gitrepository(url, branch, tag, semver, commit, timeout,
                                                                  sync_interval, ssh_private_key,
                                                                  ssh_private_key_file, https_user,
                                                                  https_key, known_hosts, known_hosts_file,
                                                                  local_auth_ref)

        # Do Validations on the Kustomization List
        if kustomization:
            validate_kustomization_list(name, kustomization)
        else:
            logger.warning(consts.NO_KUSTOMIZATIONS_WARNING)
            user_confirmation("Are you sure you want to proceed without any kustomizations?")

        # Get the protected settings and validate the private key value
        protected_settings = get_protected_settings(
            ssh_private_key, ssh_private_key_file, https_user, https_key
        )
        if consts.SSH_PRIVATE_KEY_KEY in protected_settings:
            validate_private_key(protected_settings['sshPrivateKey'])

        flux_configuration = FluxConfiguration(
            scope=scope,
            namespace=namespace,
            source_kind=dp_source_kind,
            git_repository=git_repository,
            suspend=suspend,
            kustomizations=kustomization,
            configuration_protected_settings=protected_settings,
        )

        self._validate_source_control_config_not_installed(resource_group_name, cluster_type, cluster_name)
        self._validate_extension_install(resource_group_name, cluster_rp, cluster_type, cluster_name, no_wait)

        logger.warning("Creating the flux configuration '%s' in the cluster. This may take a few minutes...", name)

        return sdk_no_wait(no_wait, self.client.begin_create_or_update, resource_group_name, cluster_rp,
                           cluster_type, cluster_name, name, flux_configuration)

    def create_source(self, resource_group_name, cluster_type, cluster_name, name, url=None, scope='cluster',
                      namespace='default', kind=consts.GIT, timeout=None, sync_interval=None, branch=None,
                      tag=None, semver=None, commit=None, local_auth_ref=None, ssh_private_key=None,
                      ssh_private_key_file=None, https_user=None, https_key=None, known_hosts=None,
                      known_hosts_file=None, no_wait=False):
        # Determine the cluster RP
        cluster_rp = get_cluster_rp(cluster_type)
        dp_source_kind = ""
        git_repository = None

        # Validate the extension install if this is not a deferred command
        if not self._is_deferred():
            self._validate_source_control_config_not_installed(resource_group_name, cluster_type, cluster_name)
            self._validate_extension_install(resource_group_name, cluster_rp, cluster_type, cluster_name, no_wait)

        if kind == consts.GIT:
            dp_source_kind = consts.GIT_REPOSITORY
            git_repository = self._validate_and_get_gitrepository(url, branch, tag, semver, commit,
                                                                  timeout, sync_interval,
                                                                  ssh_private_key, ssh_private_key_file,
                                                                  https_user, https_key, known_hosts,
                                                                  known_hosts_file, local_auth_ref)

        # Get the protected settings and validate the private key value
        protected_settings = get_protected_settings(
            ssh_private_key, ssh_private_key_file, https_user, https_key
        )
        if consts.SSH_PRIVATE_KEY_KEY in protected_settings:
            validate_private_key(protected_settings['sshPrivateKey'])

        print(protected_settings)

        flux_configuration = FluxConfiguration(
            scope=scope,
            namespace=namespace,
            source_kind=dp_source_kind,
            git_repository=git_repository,
            kustomizations=[],
            configuration_protected_settings=protected_settings,
        )

        # cache the payload if --defer used or send to Azure
        return cached_put(self.cmd, self.client.begin_create_or_update, flux_configuration,
                          resource_group_name=resource_group_name, flux_configuration_name=name,
                          cluster_rp=cluster_rp, cluster_resource_name=cluster_type,
                          cluster_name=cluster_name, setter_arg_name='flux_configuration')

    def create_kustomization(self, resource_group_name, cluster_type, cluster_name, name,
                             kustomization_name, dependencies, timeout, sync_interval,
                             retry_interval, path='', prune=False, validation='none',
                             force=False):
        # Determine ClusterRP
        cluster_rp = get_cluster_rp(cluster_type)

        # Validate the extension install if this is not a deferred command
        if not self._is_deferred():
            self._validate_source_control_config_not_installed(resource_group_name, cluster_type, cluster_name)
            self._validate_extension_install(resource_group_name, cluster_rp, cluster_type, cluster_name, no_wait=False)

        flux_configuration = cached_get(self.cmd, self.client.get, resource_group_name=resource_group_name,
                                        flux_configuration_name=name, cluster_rp=cluster_rp,
                                        cluster_resource_name=cluster_type, cluster_name=cluster_name)

        kustomization = KustomizationDefinition(
            name=name,
            path=path,
            dependencies=dependencies,
            timeout_in_seconds=timeout,
            sync_interval_in_seconds=sync_interval,
            retry_interval_in_seconds=retry_interval,
            prune=prune,
            validation=validation,
            force=force
        )

        proposed_change = flux_configuration.kustomizations[:] + [kustomization]
        validate_kustomization_list(name, proposed_change)

        upsert_to_collection(flux_configuration, 'kustomizations', kustomization, 'name')
        flux_configuration.configuration_protected_settings = None
        flux_configuration = cached_put(self.cmd, self.client.begin_create_or_update, flux_configuration,
                                        resource_group_name=resource_group_name, flux_configuration_name=name,
                                        cluster_rp=cluster_rp, cluster_resource_name=cluster_type,
                                        cluster_name=cluster_name, setter_arg_name='flux_configuration')
        return get_property(flux_configuration.kustomizations, name)

    def delete(self, resource_group_name, cluster_type, cluster_name, name, force, no_wait, yes):
        cluster_rp = get_cluster_rp(cluster_type)

        config = None
        try:
            config = self.client.get(resource_group_name, cluster_rp, cluster_type, cluster_name, name)
        except HttpResponseError:
            logger.warning("No flux configuration with name '%s' found on cluster '%s', so nothing to delete",
                           name, cluster_name)
            return None

        if has_prune_enabled(config):
            logger.warning("Prune is enabled on one or more of your kustomizations. Deleting a Flux "
                           "configuration with prune enabled will also delete the Kubernetes objects "
                           "deployed by the kustomization(s).")
            user_confirmation_factory(self.cmd, yes, "Do you want to continue?")

        if not force:
            logger.info("Deleting the flux configuration from the cluster. This may take a few minutes...")
        return sdk_no_wait(no_wait, self.client.begin_delete, resource_group_name, cluster_rp, cluster_type,
                           cluster_name, name, force_delete=force)

    def _is_deferred(self):
        if '--defer' in self.cmd.cli_ctx.data.get('safe_params'):
            return True
        return False

    def _validate_source_control_config_not_installed(self, resource_group_name, cluster_type, cluster_name):
        # Validate if we are able to install the flux configuration
        configs = self.source_control_configuration_provider.list(resource_group_name, cluster_type, cluster_name)
        # configs is an iterable, no len() so we have to iterate to check for configs
        for _ in configs:
            raise DeploymentError(
                consts.SCC_EXISTS_ON_CLUSTER_ERROR,
                consts.SCC_EXISTS_ON_CLUSTER_HELP)

    def _validate_extension_install(self, resource_group_name, cluster_rp, cluster_type, cluster_name, no_wait):
        # Validate if the extension is installed, if not, install it
        extensions = self.extension_client.list(resource_group_name, cluster_rp, cluster_type, cluster_name)
        found_flux_extension = False
        for extension in extensions:
            if extension.extension_type.lower() == consts.FLUX_EXTENSION_TYPE:
                found_flux_extension = True
                break
        if not found_flux_extension:
            logger.warning("'Microsoft.Flux' extension not found on the cluster, installing it now."
                           " This may take a few minutes...")

            extension = Extension(
                extension_type="microsoft.flux",
                auto_upgrade_minor_version=True,
                release_train=os.getenv(consts.FLUX_EXTENSION_RELEASETRAIN),
                version=os.getenv(consts.FLUX_EXTENSION_VERSION)
            )
            if not is_dogfood_cluster(self.cmd):
                extension = self.__add_identity(extension,
                                                resource_group_name,
                                                cluster_rp,
                                                cluster_type,
                                                cluster_name)

            logger.info("Starting extension creation on the cluster. This might take a minute...")
            sdk_no_wait(no_wait, self.extension_client.begin_create, resource_group_name, cluster_rp, cluster_type,
                        cluster_name, "flux", extension).result()
            logger.warning("'Microsoft.Flux' extension was successfully installed on the cluster")

    def _validate_and_get_gitrepository(self, url, branch, tag, semver, commit, timeout, sync_interval,
                                        ssh_private_key, ssh_private_key_file, https_user, https_key,
                                        known_hosts, known_hosts_file, local_auth_ref):
        # Pre-Validation
        validate_duration("--timeout", timeout)
        validate_duration("--sync-interval", sync_interval)

        # Get the known hosts data and validate it
        knownhost_data = get_data_from_key_or_file(known_hosts, known_hosts_file)
        if knownhost_data:
            validate_known_hosts(knownhost_data)
            knownhost_data = knownhost_data.strip('\n')

        # Validate registration with the RP endpoint
        validate_cc_registration(self.cmd)

        validate_git_repository(url)
        validate_url_with_params(url, ssh_private_key, ssh_private_key_file,
                                 known_hosts, known_hosts_file, https_user, https_key)

        repository_ref = validate_and_get_repository_ref(branch, tag, semver, commit)

        # Encode the https username to base64
        if https_user:
            https_user = to_base64(https_user)

        return GitRepositoryDefinition(
            url=url,
            timeout_in_seconds=get_duration(timeout),
            sync_interval_in_seconds=get_duration(sync_interval),
            repository_ref=repository_ref,
            ssh_known_hosts=knownhost_data,
            https_user=https_user,
            local_auth_ref=local_auth_ref
        )

    def __add_identity(self, extension_instance, resource_group_name, cluster_rp, cluster_type, cluster_name):
        subscription_id = get_subscription_id(self.cmd.cli_ctx)
        resources = cf_resources(self.cmd.cli_ctx, subscription_id)

        cluster_resource_id = '/subscriptions/{0}/resourceGroups/{1}/providers/{2}/{3}/{4}'.format(subscription_id,
                                                                                                   resource_group_name,
                                                                                                   cluster_rp,
                                                                                                   cluster_type,
                                                                                                   cluster_name)

        if cluster_rp == consts.MANAGED_RP_NAMESPACE:
            return extension_instance
        parent_api_version = get_parent_api_version(cluster_rp)
        try:
            resource = resources.get_by_id(cluster_resource_id, parent_api_version)
            location = str(resource.location.lower())
        except HttpResponseError as ex:
            raise ex
        identity_type = "SystemAssigned"

        extension_instance.identity = Identity(type=identity_type)
        extension_instance.location = location
        return extension_instance


def validate_and_get_repository_ref(branch, tag, semver, commit):
    validate_repository_ref(branch, tag, semver, commit)

    return RepositoryRefDefinition(
        branch=branch,
        tag=tag,
        semver=semver,
        commit=commit
    )


def get_protected_settings(ssh_private_key, ssh_private_key_file, https_user, https_key):
    protected_settings = {}
    ssh_private_key_data = get_data_from_key_or_file(ssh_private_key, ssh_private_key_file)

    # Add gitops private key data to protected settings if exists
    # Dry-run all key types to determine if the private key is in a valid format
    if ssh_private_key_data:
        protected_settings[consts.SSH_PRIVATE_KEY_KEY] = ssh_private_key_data

    # Check if both httpsUser and httpsKey exist, then add to protected settings
    if https_user and https_key:
        protected_settings[consts.HTTPS_KEY_KEY] = to_base64(https_key)

    return protected_settings
