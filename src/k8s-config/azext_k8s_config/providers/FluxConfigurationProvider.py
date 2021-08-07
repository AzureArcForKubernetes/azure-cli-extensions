# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=unused-argument

from azure.cli.core.azclierror import DeploymentError, ResourceNotFoundError
from azure.cli.core.commands import cached_get, cached_put, upsert_to_collection, get_property
from azure.core.exceptions import HttpResponseError
from knack.log import get_logger

from .._client_factory import k8s_config_fluxconfig_client
from ..utils import get_cluster_rp, get_data_from_key_or_file, get_protected_settings, get_duration
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
from .ExtensionProvider import ExtensionProvider
from .SourceControlConfigurationProvider import SourceControlConfigurationProvider

logger = get_logger(__name__)


class FluxConfigurationProvider:
    def __init__(self, cmd):
        self.extension_provider = ExtensionProvider(cmd)
        self.source_control_configuration_provider = SourceControlConfigurationProvider(cmd)
        self.cmd = cmd
        self.client = k8s_config_fluxconfig_client(cmd.cli_ctx)

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
               known_hosts_file=None, suspend=False, kustomization=None):

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
        self._validate_extension_install(resource_group_name, cluster_type, cluster_name)

        logger.warning("Creating the fluxConfiguration '%s' in the cluster. This may take a minute...", name)

        return self.client.begin_create_or_update(resource_group_name, cluster_rp,
                                                  cluster_type, cluster_name, name, flux_configuration)

    def create_source(self, resource_group_name, cluster_type, cluster_name, name, url=None, scope='cluster',
                      namespace='default', kind=consts.GIT, timeout=None, sync_interval=None, branch=None,
                      tag=None, semver=None, commit=None, local_auth_ref=None, ssh_private_key=None,
                      ssh_private_key_file=None, https_user=None, https_key=None, known_hosts=None,
                      known_hosts_file=None):
        # Determine the cluster RP
        cluster_rp = get_cluster_rp(cluster_type)
        dp_source_kind = ""
        git_repository = None

        # Validate the extension install if this is not a deferred command
        if not self._is_deferred():
            self._validate_source_control_config_not_installed(resource_group_name, cluster_type, cluster_name)
            self._validate_extension_install(resource_group_name, cluster_type, cluster_name)

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
            self._validate_extension_install(resource_group_name, cluster_type, cluster_name)

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

    def delete(self, resource_group_name, cluster_type, cluster_name, name, force):
        cluster_rp = get_cluster_rp(cluster_type)

        if not force:
            logger.info("Delting the flux configuration from the cluster. This may take a minute...")
        return self.client.begin_delete(resource_group_name, cluster_rp, cluster_type,
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

    def _validate_extension_install(self, resource_group_name, cluster_type, cluster_name):
        # Validate if the extension is installed, if not, install it
        extensions = self.extension_provider.list(resource_group_name, cluster_type, cluster_name)
        found_flux_extension = False
        for extension in extensions:
            if extension.extension_type.lower() == consts.FLUX_EXTENSION_TYPE:
                found_flux_extension = True
                break
        if not found_flux_extension:
            logger.warning("'Micrsoft.Flux' extension not found on the cluster, installing it now."
                           " This may take a minute...")
            self.extension_provider.create(resource_group_name, cluster_type, cluster_name,
                                           "flux", consts.FLUX_EXTENSION_TYPE).result()
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

        # Validate registration with the RP endpoint
        validate_cc_registration(self.cmd)

        validate_git_repository(url)
        validate_url_with_params(url, ssh_private_key, ssh_private_key_file,
                                 known_hosts, known_hosts_file, https_user, https_key)

        repository_ref = validate_and_get_repository_ref(branch, tag, semver, commit)

        return GitRepositoryDefinition(
            url=url,
            timeout_in_seconds=get_duration(timeout),
            sync_interval_in_seconds=get_duration(sync_interval),
            repository_ref=repository_ref,
            ssh_known_hosts=knownhost_data,
            https_user=https_user,
            local_auth_ref=local_auth_ref
        )


def validate_and_get_repository_ref(branch, tag, semver, commit):
    validate_repository_ref(branch, tag, semver, commit)

    return RepositoryRefDefinition(
        branch=branch,
        tag=tag,
        semver=semver,
        commit=commit
    )
