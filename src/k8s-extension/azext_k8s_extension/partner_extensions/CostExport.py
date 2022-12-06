import logging
import datetime
import time
import shlex
from logging import Logger

from typing import TypedDict

from knack.log import get_logger

from azure.cli.core import AzCli
from azure.cli.core.azclierror import CLIInternalError, ValidationError
from azure.cli.core.commands.client_factory import get_mgmt_service_client, get_subscription_id
from azure.cli.core.profiles import ResourceType
from azure.cli.core import get_default_cli
from azure.mgmt.core.tools import parse_resource_id

from ..vendored_sdks.models import Extension
from ..vendored_sdks.models import ScopeCluster
from ..vendored_sdks.models import Scope

from .DefaultExtension import DefaultExtension

logger: Logger = get_logger(__name__)
logger.addHandler(logging.StreamHandler())


class CostExport(DefaultExtension):
    def __init__(self):
        self.DEFAULT_RELEASE_NAMESPACE = 'cost-export'

    def Create(self, cmd, client, resource_group_name, cluster_name, name, cluster_type, extension_type,
               scope, auto_upgrade_minor_version, release_train, version, target_namespace,
               release_namespace, configuration_settings, configuration_protected_settings,
               configuration_settings_file, configuration_protected_settings_file):
        logger.info("Creating CostExport extension")
        subscription: str = get_subscription_id(cmd.cli_ctx)
        mc_resource_group = _mc_resource_group(subscription=subscription, resource_group_name=resource_group_name,
                                               cluster_name=cluster_name)
        if 'storageAccountId' not in configuration_settings:
            raise ValidationError("configuration-settings", "storageAccountId is required")
        if 'storageContainer' not in configuration_settings:
            raise ValidationError("configuration-settings", "storageContainer is required")
        if 'storagePath' not in configuration_settings:
            configuration_settings['storagePath'] = mc_resource_group
        if 'cmStorageAccountId' not in configuration_settings:
            configuration_settings['cmStorageAccountId'] = configuration_settings['storageAccountId']
        if 'cmStorageContainer' not in configuration_settings:
            configuration_settings['cmStorageContainer'] = configuration_settings['storageContainer']
        if 'cmStoragePath' not in configuration_settings:
            configuration_settings['cmStoragePath'] = configuration_settings['storagePath']

        configuration_settings["clusterResourceGroup"] = mc_resource_group
        configuration_settings["subscriptionId"] = subscription

        _register_resource_provider(cmd, "Microsoft.CostManagementExports")

        _ensure_storage_container(
            storage_account_id=configuration_settings['storageAccountId'],
            storage_container=configuration_settings['storageContainer'],
        )

        # resource group name limit is 90 chars
        # SP name limit is more than len(cost-export-) + 90
        sp_name = "cost-export-" + mc_resource_group
        sp = _create_service_principal(sp_name=sp_name)
        configuration_protected_settings["servicePrincipal.appId"] = sp["appId"]
        configuration_protected_settings["servicePrincipal.tenant"] = sp["tenant"]
        configuration_protected_settings["servicePrincipal.password"] = sp["password"]
        configuration_protected_settings["servicePrincipal.displayName"] = sp["displayName"]

        _invoke(["role", "assignment", "create",
                 "--assignee", sp["appId"],
                 "--role", "Storage Blob Data Contributor",
                 "--scope", configuration_settings['storageAccountId']
                 ])

        if configuration_settings['cmStorageAccountId'] != configuration_settings['storageAccountId']:
            _invoke(["role", "assignment", "create",
                     "--assignee", sp["appId"],
                     "--role", "Storage Blob Data Contributor",
                     "--scope", configuration_settings['cmStorageAccountId']
                     ])

        _invoke(["role", "assignment", "create",
                 "--assignee", sp["appId"],
                 "--role", "Reader",
                 "--scope", "/subscriptions/" + subscription + "/resourceGroups/" + mc_resource_group])

        # cost export automatically append the export name (cluster_name in our case) to the path
        # so we need to adjust the value we pass to the exporter
        configuration_settings['cmStoragePath'] = _create_cost_export(
            subscription=subscription,
            cluster_name=cluster_name,
            storage_account_id=configuration_settings['cmStorageAccountId'],
            mc_resource_group=mc_resource_group,
            storage_container=configuration_settings['cmStorageContainer'],
            storage_directory=configuration_settings['cmStoragePath'],
        )

        extension = Extension(
            extension_type=extension_type,
            auto_upgrade_minor_version=auto_upgrade_minor_version,
            release_train=release_train,
            version=version,
            scope=Scope(cluster=ScopeCluster(release_namespace=release_namespace), namespace=None),
            configuration_settings=configuration_settings,
            configuration_protected_settings=configuration_protected_settings,
        )
        create_identity = True
        logger.info("deploying helm in cluster")
        return extension, name, create_identity


def _register_resource_provider(cmd, resource_provider):
    if _is_resource_provider_registered(cmd, resource_provider):
        logger.info("Resource provider '%s' is already registered.", resource_provider)
        return
    from azure.mgmt.resource.resources.models import ProviderRegistrationRequest, ProviderConsentDefinition

    logger.warning("Registering resource provider %s ...", resource_provider)
    properties = ProviderRegistrationRequest(
        third_party_provider_consent=ProviderConsentDefinition(consent_to_authorization=True))

    client = _providers_client_factory(cmd.cli_ctx)
    try:
        client.register(resource_provider, properties=properties)
        # wait for registration to finish
        timeout_secs = 120
        registration = _is_resource_provider_registered(cmd, resource_provider)
        start = time.time()
        while not registration:
            registration = _is_resource_provider_registered(cmd, resource_provider)
            time.sleep(3)
            if (time.time() - start) >= timeout_secs:
                raise CLIInternalError(
                    f"Timed out while waiting for the {resource_provider} resource provider to be registered.")
    except Exception as e:
        msg = ("This operation requires requires registering the resource provider {0}. "
               "We were unable to perform that registration on your behalf: "
               "Server responded with error message -- {1} . "
               "Please check with your admin on permissions, "
               "or try running registration manually with: az provider register --wait --namespace {0}")
        raise ValidationError(resource_provider, msg.format(e.args)) from e
    logger.info("Resource provider '%s' is now registered.", resource_provider)


def _is_resource_provider_registered(cmd, resource_provider, subscription_id=None) -> bool:
    if not subscription_id:
        subscription_id = get_subscription_id(cmd.cli_ctx)
    try:
        providers_client = _providers_client_factory(cmd.cli_ctx, subscription_id)
        registration_state = getattr(providers_client.get(resource_provider), 'registration_state', "NotRegistered")

        return bool(registration_state and registration_state.lower() == 'registered')
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Failed to get resource provider %s: %s", resource_provider, e)
        return False


def _providers_client_factory(cli_ctx, subscription_id=None):
    return get_mgmt_service_client(cli_ctx, ResourceType.MGMT_RESOURCE_RESOURCES,
                                   subscription_id=subscription_id).providers


def _create_cost_export(subscription: str, mc_resource_group: str, cluster_name: str, storage_account_id: str,
                        storage_container: str, storage_directory: str) -> str:
    args = [
        "costmanagement", "export", "create",
        "--name", cluster_name,
        "--scope", f"/subscriptions/{subscription}/resourceGroups/{mc_resource_group}",
        "--timeframe", "MonthToDate",
        "--recurrence-period", f"from={datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        "to=2200-01-01T00:00:00",
        "--recurrence", "Daily",
        "--schedule-status", "Active",
        "--storage-account-id", storage_account_id,
        "--storage-container", storage_container,
        "--storage-directory", storage_directory,
        "--query", "'id'",
        "--subscription", subscription
    ]

    # AmortizedCost provides the most accurate cost data, but it's not available for all subscriptions
    for export_type in ["AmortizedCost", "Usage"]:
        cli = _cli()
        cli.invoke(args + ["--type", export_type])
        if cli.result.exit_code == 0:
            logger.info("created cost export with '%s' type", export_type)
            return storage_directory + "/" + cluster_name
        else:
            logger.info("couldn't create export with '%s' type", export_type)
    # raise last error
    raise cli.result.error


def _mc_resource_group(subscription: str, resource_group_name: str, cluster_name: str) -> str:
    cli = _cli()
    cli.invoke(["aks", "show",
                "--subscription", subscription,
                "--resource-group", resource_group_name,
                "-n", cluster_name])
    if cli.result.exit_code != 0:
        raise Exception("Unable to get cluster resource group")
    return cli.result.result['nodeResourceGroup']


def _ensure_storage_container(storage_account_id: str, storage_container: str):
    resource = parse_resource_id(storage_account_id)
    try:
        _invoke(["storage", "account", "show", "--ids", storage_account_id])
    except SystemExit as e:
        if e.code != 3:
            raise e
        create_storage_args = ["storage", "account", "create",
                               "--resource-group", resource['resource_group'],
                               "--name", resource['name'],
                               "--subscription", resource['subscription'],
                               "--allow-blob-public-access", "false"]
        _invoke(create_storage_args)
        logger.info("created storage account %s", storage_account_id)
    cli = _invoke(["storage", "container", "exists", "--name", storage_container, "--account-name", resource["name"],
                   "--auth-mode", "login"])
    if cli.result.result['exists']:
        return
    _invoke(["storage", "container", "create", "--name", storage_container, "--account-name", resource["name"],
             "--auth-mode", "login"])
    logger.info("created new container %s for %s", storage_container, storage_account_id)


class ServicePrincipal(TypedDict):
    appId: str
    password: str
    tenant: str
    displayName: str


def _create_service_principal(sp_name: str) -> ServicePrincipal:
    cli = _invoke(["ad", "sp", "create-for-rbac", "--display-name", sp_name, "--years", "2"])
    logger.info("created service principal %s", sp_name)
    return cli.result.result


def _cli() -> AzCli:
    return get_default_cli()


def _invoke(args) -> AzCli:
    cli = _cli()
    try:
        cli.invoke(args)
    except SystemExit as e:
        cmd = shlex.join(["az"] + args)
        # TODO: is it helpful enough?
        # it seems like the error message is logged inside invokation and isn't available here
        logger.error("An error during setup step. Check your permissions or try to run it manually:\n %s", cmd)
        raise e
    if cli.result.exit_code != 0:
        cmd = shlex.join(["az"] + args)
        raise Exception(f"Unexpected non-zero exit code ({cli.result.exit_code}) during command execution: {cmd}")
    return cli
