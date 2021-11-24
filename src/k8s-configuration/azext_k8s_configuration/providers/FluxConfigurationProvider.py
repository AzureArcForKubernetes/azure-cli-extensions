# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=unused-argument

import os

from azure.cli.core.azclierror import DeploymentError, ResourceNotFoundError, ValidationError, \
    UnrecognizedArgumentError, RequiredArgumentMissingError
from azure.cli.core.util import sdk_no_wait
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
    parse_dependencies,
    parse_duration,
    has_prune_enabled,
    to_base64,
    is_dogfood_cluster
)
from ..validators import (
    validate_cc_registration,
    validate_git_url,
    validate_known_hosts,
    validate_repository_ref,
    validate_duration,
    validate_private_key,
    validate_url_with_params
)
from .. import consts
from ..vendored_sdks.v2022_01_01_preview.models import (
    FluxConfiguration,
    FluxConfigurationPatch,
    GitRepositoryDefinition,
    GitRepositoryPatchDefinition,
    BucketDefinition,
    RepositoryRefDefinition,
    KustomizationDefinition,
    KustomizationPatchDefinition,
    DependsOnDefinition
)
from ..vendored_sdks.v2021_09_01.models import (
    Extension,
    Identity
)
from .SourceControlConfigurationProvider import SourceControlConfigurationProvider

logger = get_logger(__name__)


class FluxConfigurationProvider:
    def __init__(self, cmd, resource_group_name, cluster_type, cluster_name, name=None, no_wait=False, yes=False):
        self.extension_client = k8s_configuration_extension_client(cmd.cli_ctx)
        self.source_control_configuration_provider = SourceControlConfigurationProvider(cmd)
        self.cmd = cmd
        self.client = k8s_configuration_fluxconfig_client(cmd.cli_ctx)
        self.resource_group_name = resource_group_name
        self.cluster_type = cluster_type
        self.cluster_rp = get_cluster_rp(self.cluster_type)
        self.cluster_name = cluster_name
        self.name = name
        self.no_wait = no_wait
        self.yes = yes
        validate_cc_registration(self.cmd)

    def show(self):
        """Get an existing Kubernetes Source Control Configuration.
        """

        try:
            config = self.client.get(self.resource_group_name, self.cluster_rp, self.cluster_type, self.cluster_name, self.name)
            return config
        except HttpResponseError as ex:
            # Customize the error message for resources not found
            if ex.response.status_code == 404:
                # If Cluster not found
                if ex.message.__contains__("(ResourceNotFound)"):
                    message = ex.message
                    recommendation = 'Verify that the --cluster-type is correct and the Resource ' \
                                     '{0}/{1}/{2} exists'.format(self.cluster_rp, self.cluster_type, self.cluster_name)
                # If Configuration not found
                elif ex.message.__contains__("Operation returned an invalid status code 'Not Found'"):
                    message = '(FluxConfigurationNotFound) The Resource {0}/{1}/{2}/' \
                              'Microsoft.KubernetesConfiguration/fluxConfigurations/{3} ' \
                              'could not be found!' \
                              .format(self.cluster_rp, self.cluster_type, self.cluster_name, self.name)
                    recommendation = 'Verify that the Resource {0}/{1}/{2}/Microsoft.KubernetesConfiguration' \
                                     '/fluxConfigurations/{3} exists'.format(self.cluster_rp, self.cluster_type,
                                                                             self.cluster_name, self.name)
                else:
                    message = ex.message
                    recommendation = ''
                raise ResourceNotFoundError(message, recommendation) from ex
            raise ex

    def list(self):
        cluster_rp = get_cluster_rp(self.cluster_type)
        return self.client.list(self.resource_group_name, self.cluster_rp, self.cluster_type, self.cluster_name)

    # pylint: disable=too-many-locals
    def create(self, **kwargs):
        factory = source_kind_generator_factory(**kwargs)
        git_repository, bucket = factory.generate()

        kustomizations = kwargs.get('kustomization')
        if kustomizations:
            # Convert the Internal List Representation of Kustomization to Dictionary
            kustomizations = {k.name: k.to_KustomizationDefinition() for k in kustomizations}
        else:
            logger.warning(consts.NO_KUSTOMIZATIONS_WARNING)
            kustomizations = {
                consts.DEFAULT_KUSTOMIZATION_NAME: KustomizationDefinition()
            }

        # Get the protected settings and validate the private key value
        protected_settings = get_protected_settings(
            kwargs.get('ssh_private_key'), kwargs.get('ssh_private_key_file'), kwargs.get('https_key'), kwargs.get('secret_key')
        )
        if protected_settings and consts.SSH_PRIVATE_KEY_KEY in protected_settings:
            validate_private_key(protected_settings['sshPrivateKey'])

        flux_configuration = FluxConfiguration(
            scope=kwargs.get('scope'),
            namespace=kwargs.get('namespace'),
            source_kind=factory.get_rp_source_kind(),
            git_repository=git_repository,
            bucket=bucket,
            suspend=kwargs.get('suspend'),
            kustomizations=kustomizations,
            configuration_protected_settings=protected_settings,
        )

        self._validate_source_control_config_not_installed()
        self._validate_extension_install()

        logger.warning("Creating the flux configuration '%s' in the cluster. This may take a few minutes...", self.name)

        return sdk_no_wait(self.no_wait, self.client.begin_create_or_update, self.resource_group_name, self.cluster_rp,
                           self.cluster_type, self.cluster_name, self.name, flux_configuration)

    def update(self, **kwargs):
        config = self.show()
        kind = kwargs.get('kind')

        if not kind:
            kind = config.source_kind
        factory = source_kind_generator_factory(**kwargs)
        git_repository, bucket = factory.generate_patch()

        kustomizations = kwargs.get('kustomization')
        if kustomizations:
            # Convert the Internal List Representation of Kustomization to Dictionary
            kustomizations = {k.name: k.to_KustomizationPatchDefinition() for k in kustomizations}

        # Get the protected settings and validate the private key value
        protected_settings = get_protected_settings(
            kwargs.get('ssh_private_key'), kwargs.get('ssh_private_key_file'), kwargs.get('https_key'), kwargs.get('secret_key')
        )
        if protected_settings and consts.SSH_PRIVATE_KEY_KEY in protected_settings:
            validate_private_key(protected_settings['sshPrivateKey'])

        flux_configuration = FluxConfigurationPatch(
            suspend=kwargs.get('suspend'),
            git_repository=git_repository,
            bucket=bucket,
            kustomizations=kustomizations,
            configuration_protected_settings=protected_settings,
        )

        return sdk_no_wait(self.no_wait, self.client.begin_update, self.resource_group_name, self.cluster_rp,
                           self.cluster_type, self.cluster_name, self.name, flux_configuration)

    def create_kustomization(self, **kwargs):
        kustomization_name = kwargs.get('kustomization_name')
        dependencies = kwargs.get('dependencies')
        timeout = kwargs.get('timeout')
        sync_interval = kwargs.get('sync_interval')
        retry_interval = kwargs.get('retry_interval')
        

        # Pre-Validation
        validate_duration("--timeout", timeout)
        validate_duration("--sync-interval", sync_interval)
        validate_duration("--retry-interval", retry_interval)

        current_config = self.show()
        if kustomization_name in current_config.kustomizations:
            raise ValidationError(
                consts.CREATE_KUSTOMIZATION_EXIST_ERROR.format(kustomization_name, self.name),
                consts.CREATE_KUSTOMIZATION_EXIST_HELP
            )

        # Add the dependencies in their model to the kustomization
        model_dependencies = None
        if dependencies:
            model_dependencies = []
            for dep in parse_dependencies(dependencies):
                model_dependencies.append(
                    DependsOnDefinition(
                        kustomization_name=dep
                    )
                )

        kustomization = {
            kustomization_name: KustomizationDefinition(
                path=kwargs.get('path'),
                depends_on=model_dependencies,
                timeout_in_seconds=parse_duration(timeout),
                sync_interval_in_seconds=parse_duration(sync_interval),
                retry_interval_in_seconds=parse_duration(retry_interval),
                prune=kwargs.get('prune'),
                force=kwargs.get('force')
            )
        }
        flux_configuration_patch = FluxConfigurationPatch(
            kustomizations=kustomization
        )
        return sdk_no_wait(self.no_wait, self.client.begin_update, self.resource_group_name, self.cluster_rp,
                           self.cluster_type, self.cluster_name, self.name, flux_configuration_patch)

    def update_kustomization(self, **kwargs):
        kustomization_name = kwargs.get('kustomization_name')
        dependencies = kwargs.get('dependencies')
        timeout = kwargs.get('timeout')
        sync_interval = kwargs.get('sync_interval')
        retry_interval = kwargs.get('retry_interval')

        # Pre-Validation
        validate_duration("--timeout", timeout)
        validate_duration("--sync-interval", sync_interval)
        validate_duration("--retry-interval", retry_interval)

        current_config = self.show()
        if kustomization_name not in current_config.kustomizations:
            raise ValidationError(
                consts.UPDATE_KUSTOMIZATION_NO_EXIST_ERROR.format(kustomization_name, self.name),
                consts.UPDATE_KUSTOMIZATION_NO_EXIST_HELP
            )

        # Add the dependencies in their model to the kustomization
        model_dependencies = None
        if dependencies:
            model_dependencies = []
            for dep in parse_dependencies(dependencies):
                model_dependencies.append(
                    DependsOnDefinition(
                        kustomization_name=dep
                    )
                )

        kustomization = {
            kustomization_name: KustomizationDefinition(
                path=kwargs.get('path'),
                depends_on=model_dependencies,
                timeout_in_seconds=parse_duration(timeout),
                sync_interval_in_seconds=parse_duration(sync_interval),
                retry_interval_in_seconds=parse_duration(retry_interval),
                prune=kwargs.get('prune'),
                force=kwargs.get('force')
            )
        }
        flux_configuration_patch = FluxConfigurationPatch(
            kustomizations=kustomization
        )
        return sdk_no_wait(self.no_wait, self.client.begin_update, self.resource_group_name, self.cluster_rp,
                           self.cluster_type, self.cluster_name, self.name, flux_configuration_patch)

    def delete_kustomization(self, kustomization_name):
        # Confirmation message for deletes
        user_confirmation_factory(self.cmd, self.yes)

        current_config = self.show()
        if kustomization_name not in current_config.kustomizations:
            raise ValidationError(
                consts.DELETE_KUSTOMIZATION_NO_EXIST_ERROR.format(kustomization_name, self.name),
                consts.DELETE_KUSTOMIZATION_NO_EXIST_HELP
            )

        if current_config.kustomizations[kustomization_name].prune:
            logger.warning("Prune is enabled on this kustomization. Deleting a kustomization "
                           "with prune enabled will also delete the Kubernetes objects "
                           "deployed by the kustomization.")
            user_confirmation_factory(self.cmd, self.yes, "Do you want to continue?")

        kustomization = {
            kustomization_name: None
        }
        flux_configuration_patch = FluxConfigurationPatch(
            kustomizations=kustomization
        )
        return sdk_no_wait(self.no_wait, self.client.begin_update, self.resource_group_name, self.cluster_rp,
                           self.cluster_type, self.cluster_name, self.name, flux_configuration_patch)

    def list_kustomization(self):
        # Determine ClusterRP
        current_config = self.show()
        return current_config.kustomizations

    def show_kustomization(self, kustomization_name):
        current_config = self.show()
        if kustomization_name not in current_config.kustomizations:
            raise ValidationError(
                consts.SHOW_KUSTOMIZATION_NO_EXIST_ERROR.format(kustomization_name),
                consts.SHOW_KUSTOMIZATION_NO_EXIST_HELP
            )
        return {kustomization_name: current_config.kustomizations[kustomization_name]}

    def delete(self, force):
        # Confirmation message for deletes
        user_confirmation_factory(self.cmd, self.yes)

        config = None
        try:
            config = self.show()
        except HttpResponseError:
            logger.warning("No flux configuration with name '%s' found on cluster '%s', so nothing to delete",
                           self.name, self.cluster_name)
            return None

        if has_prune_enabled(config):
            logger.warning("Prune is enabled on one or more of your kustomizations. Deleting a Flux "
                           "configuration with prune enabled will also delete the Kubernetes objects "
                           "deployed by the kustomization(s).")
            user_confirmation_factory(self.cmd, self.yes, "Do you want to continue?")

        if not force:
            logger.info("Deleting the flux configuration from the cluster. This may take a few minutes...")
        return sdk_no_wait(self.no_wait, self.client.begin_delete, self.resource_group_name, self.cluster_rp, self.cluster_type,
                           self.cluster_name, self.name, force_delete=force)

    def _is_deferred(self):
        if '--defer' in self.cmd.cli_ctx.data.get('safe_params'):
            return True
        return False

    def _validate_source_control_config_not_installed(self):
        # Validate if we are able to install the flux configuration
        configs = self.source_control_configuration_provider.list(self.resource_group_name, self.cluster_type, self.cluster_name)
        # configs is an iterable, no len() so we have to iterate to check for configs
        for _ in configs:
            raise DeploymentError(
                consts.SCC_EXISTS_ON_CLUSTER_ERROR,
                consts.SCC_EXISTS_ON_CLUSTER_HELP)

    def _validate_extension_install(self):
        # Validate if the extension is installed, if not, install it
        extensions = self.extension_client.list(self.resource_group_name, self.cluster_rp, self.cluster_type, self.cluster_name)
        flux_extension = None
        for extension in extensions:
            if extension.extension_type.lower() == consts.FLUX_EXTENSION_TYPE:
                flux_extension = extension
                break
        if not flux_extension:
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
                                                self.resource_group_name,
                                                self.cluster_rp,
                                                self.cluster_type,
                                                self.cluster_name)

            logger.info("Starting extension creation on the cluster. This might take a few minutes...")
            sdk_no_wait(self.no_wait, self.extension_client.begin_create, self.resource_group_name, self.cluster_rp, self.cluster_type,
                        self.cluster_name, "flux", extension).result()
            # Only show that we have received a success when we have --no-wait
            if not self.no_wait:
                logger.warning("'Microsoft.Flux' extension was successfully installed on the cluster")
        elif flux_extension.provisioning_state == consts.CREATING:
            raise DeploymentError(
                consts.FLUX_EXTENSION_CREATING_ERROR,
                consts.FLUX_EXTENSION_CREATING_HELP
            )
        elif flux_extension.provisioning_state != consts.SUCCEEDED:
            raise DeploymentError(
                consts.FLUX_EXTENSION_NOT_SUCCEEDED_OR_CREATING_ERROR,
                consts.FLUX_EXTENSION_NOT_SUCCEEDED_OR_CREATING_HELP
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


def source_kind_generator_factory(kind=consts.GIT, **kwargs):
    if kind == consts.GIT or kind == consts.GIT_REPOSITORY:
        return GitRepositoryGenerator(**kwargs)
    else:
        return BucketGenerator(**kwargs)

class SourceKindGenerator:
    def __init__(self, kind, required_params, invalid_params):
        self.kind = kind
        self.invalid_params = invalid_params
        self.required_params = required_params

    def validate_required_params(self, **kwargs):
        copied_required = self.required_params.copy()
        for kwarg, value in kwargs.items():
            if value:
                copied_required.discard(kwarg)
        if len(copied_required) > 0:
            raise RequiredArgumentMissingError(
                consts.REQUIRED_VALUES_MISSING_ERROR.format(', '.join(copied_required), self.kind),
                consts.REQUIRED_VALUES_MISSING_HELP
            )

    def validate_params(self, **kwargs):
        bad_args = []
        for kwarg, value in kwargs.items():
            if value and kwarg in self.invalid_params:
                bad_args.append(kwarg)
        if len(bad_args) > 0:
            raise UnrecognizedArgumentError(
                consts.EXTRA_VALUES_PROVIDED_ERROR.format(', '.join(bad_args), self.kind),
                consts.EXTRA_VALUES_PROVIDED_HELP
            )
    
    def get_rp_source_kind(self):
        if self.kind == consts.GIT:
            return consts.GIT_REPOSITORY
        else:
            return consts.BUCKET

class GitRepositoryGenerator(SourceKindGenerator):
    def __init__(self, **kwargs):
        # Common Pre-Validation
        super().__init__(consts.GIT, consts.GIT_REPO_REQUIRED_PARAMS, consts.GIT_REPO_INVALID_PARAMS)
        super().validate_required_params(**kwargs)
        super().validate_params(**kwargs)

        # Pre-Validation
        validate_duration("--timeout", kwargs.get('timeout'))
        validate_duration("--sync-interval", kwargs.get('sync_interval'))

        self.kwargs = kwargs
        self.url = kwargs.get('url')
        self.timeout = kwargs.get('timeout')
        self.sync_interval = kwargs.get('sync_interval')
        self.local_auth_ref = kwargs.get('local_auth_ref')
        self.known_hosts = kwargs.get('known_hosts')
        self.known_hosts_file = kwargs.get('known_hosts_file')
        self.ssh_private_key = kwargs.get('ssh_private_key')
        self.ssh_private_key_file = kwargs.get('ssh_private_key_file')
        self.https_user = kwargs.get('https_user')
        self.https_key = kwargs.get('https_key')

        # Get the known hosts data and validate it
        self.knownhost_data = get_data_from_key_or_file(kwargs.get('known_hosts'), kwargs.get('known_hosts_file'), strip_newline=True)
        if self.knownhost_data:
            validate_known_hosts(self.knownhost_data)

        self.https_ca_data = get_data_from_key_or_file(kwargs.get('https_ca_cert'), kwargs.get('https_ca_cert_file'), strip_newline=True)
        self.repository_ref = None
        if any([kwargs.get('branch'), kwargs.get('tag'), kwargs.get('semver'), kwargs.get('commit')]):
            self.repository_ref = RepositoryRefDefinition(
                branch=kwargs.get('branch'),
                tag=kwargs.get('tag'),
                semver=kwargs.get('semver'),
                commit=kwargs.get('commit')
            )

    '''
    generate(self) generates the GitRepository object for the PUT case
    '''
    def generate(self):
        validate_git_url(self.url)
        validate_url_with_params(self.url, self.ssh_private_key, self.ssh_private_key_file,
                                 self.known_hosts, self.known_hosts_file, self.https_user, self.https_key)
        validate_repository_ref(self.repository_ref)
        return GitRepositoryDefinition(
            url=self.url,
            timeout_in_seconds=parse_duration(self.timeout),
            sync_interval_in_seconds=parse_duration(self.sync_interval),
            repository_ref=self.repository_ref,
            ssh_known_hosts=self.knownhost_data,
            https_user=self.https_user,
            local_auth_ref=self.local_auth_ref,
            https_ca_file=self.https_ca_data
        ), None

    '''
    generate_patch(self) generates the GitRepository object for the PATCH case
    The patch only returns non-null values if the user has specified a value for the parameter
    '''
    def generate_patch(self):
        if any(self.kwargs.values()):
            return GitRepositoryPatchDefinition(
                url=self.url,
                timeout_in_seconds=parse_duration(self.timeout),
                sync_interval_in_seconds=parse_duration(self.sync_interval),
                repository_ref=self.repository_ref,
                ssh_known_hosts=self.knownhost_data,
                https_user=self.https_user,
                local_auth_ref=self.local_auth_ref,
                https_ca_file=self.https_ca_data
            ), None
        return None, None

class BucketGenerator(SourceKindGenerator):
    def __init__(self, **kwargs):
        # Common Pre-Validation
        super().__init__(consts.BUCKET, consts.BUCKET_REQUIRED_PARAMS, consts.BUCKET_INVALID_PARAMS)
        super().validate_required_params(**kwargs)
        super().validate_params(**kwargs)

        # Pre-Validations
        validate_duration("--timeout", kwargs.get('timeout'))
        validate_duration("--sync-interval", kwargs.get('sync_interval'))

        self.kwargs = kwargs
        self.url = kwargs.get('url')
        self.bucket_name = kwargs.get('bucket_name')
        self.timeout = kwargs.get('timeout')
        self.sync_interval = kwargs.get('sync_interval')
        self.access_key = kwargs.get('access_key')
        self.local_auth_ref = kwargs.get('local_auth_ref')
        self.insecure = kwargs.get('insecure')
    
    '''
    generate(self) generates the Bucket object for the PUT case
    '''
    def generate(self): 
        return None, BucketDefinition(
            url=self.url,
            bucket_name=self.bucket_name,
            timeout_in_seconds=parse_duration(self.timeout),
            sync_interval_in_seconds=parse_duration(self.sync_interval),
            access_key=self.access_key,
            local_auth_ref=self.local_auth_ref,
            insecure=self.insecure
        )
    
    '''
    generate_patch(self) generates the Bucket object for the PATCH case
    The patch only returns non-null values if the user has specified a value for the parameter
    '''
    def generate_patch(self):
        if any(self.kwargs.values()):
            return None, BucketDefinition(
                url=self.url,
                bucket_name=self.bucket_name,
                timeout_in_seconds=parse_duration(self.timeout),
                sync_interval_in_seconds=parse_duration(self.sync_interval),
                access_key=self.access_key,
                local_auth_ref=self.local_auth_ref,
                insecure=self.insecure
            )
        return None, None


def get_protected_settings(ssh_private_key, ssh_private_key_file, https_key, secret_key):
    protected_settings = {}
    ssh_private_key_data = get_data_from_key_or_file(ssh_private_key, ssh_private_key_file)

    # Add gitops private key data to protected settings if exists
    if ssh_private_key_data:
        protected_settings[consts.SSH_PRIVATE_KEY_KEY] = ssh_private_key_data

    if https_key:
        protected_settings[consts.HTTPS_KEY_KEY] = to_base64(https_key)

    if secret_key:
        protected_settings[consts.BUCKET_SECRET_KEY_KEY] = to_base64(secret_key)

    # Return the protected settings dict if there are any values there
    return protected_settings if len(protected_settings) > 0 else None
