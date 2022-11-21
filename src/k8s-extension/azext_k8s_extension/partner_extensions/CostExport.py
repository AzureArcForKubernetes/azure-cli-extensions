import logging

import datetime
import time

from azure.cli.core import AzCli
from azure.cli.core.azclierror import CLIInternalError, ValidationError
from azure.cli.core.profiles import ResourceType
from .DefaultExtension import DefaultExtension
from azure.cli.core import get_default_cli
from ..vendored_sdks.models import Extension
from ..vendored_sdks.models import ScopeCluster
from ..vendored_sdks.models import Scope
from azure.cli.core.commands.client_factory import get_mgmt_service_client, get_subscription_id
from knack.log import get_logger
from logging import Logger

logger: Logger = get_logger(__name__)
logger.addHandler(logging.StreamHandler())


class CostExport(DefaultExtension):
    def __init__(self):
        self.DEFAULT_RELEASE_NAMESPACE = 'cost-export'

    # Configuration parameters:
    # storage-account-resource-id
    # storage-account-name
    # storage-container-name

    def Create(self, cmd, client, resource_group_name, cluster_name, name, cluster_type, extension_type,
               scope, auto_upgrade_minor_version, release_train, version, target_namespace,
               release_namespace, configuration_settings, configuration_protected_settings,
               configuration_settings_file, configuration_protected_settings_file):
        logger.info("Creating CostExport extension")

        storage_account_name = configuration_settings.get('storage-account-name', None)
        if not storage_account_name:
            raise ValidationError("config parameter storage-account-name is required")
        storage_container_name = configuration_settings.get('storage-container', "costexport")
        storage_resource_group = configuration_settings.get('storage-resource-group', resource_group_name)
        subscription: str = get_subscription_id(cmd.cli_ctx)

        _ensure_storage_container(
            subscription_id=subscription,
            resource_group_name=storage_resource_group,
            storage_account_name=storage_account_name,
            storage_container_name=storage_container_name,
        )
        _register_resource_provider(cmd, "Microsoft.CostManagementExports")
        # use cluster resource group if not specified
        _create_cost_export(
            subscription=subscription,
            cluster_name=cluster_name,
            resource_group_name=resource_group_name,
            storage_account_name=storage_account_name,
            storage_resource_group_name=storage_resource_group
        )

        # Default validations & defaults for Create
        release_namespace = self.DEFAULT_RELEASE_NAMESPACE
        scope_cluster = ScopeCluster(release_namespace=release_namespace)
        ext_scope = Scope(cluster=scope_cluster, namespace=None)
        extension = Extension(
            extension_type=extension_type,
            auto_upgrade_minor_version=auto_upgrade_minor_version,
            release_train=release_train,
            version=version,
            scope=ext_scope,
            configuration_settings=configuration_settings,
            configuration_protected_settings=configuration_protected_settings,
        )
        create_identity = True
        return extension, name, create_identity


def _register_resource_provider(cmd, resource_provider):
    if _is_resource_provider_registered(cmd, resource_provider):
        logger.info("Resource provider '%s' is already registered.", resource_provider)
        return
    from azure.mgmt.resource.resources.models import ProviderRegistrationRequest, ProviderConsentDefinition

    logger.warning(f"Registering resource provider {resource_provider} ...")
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


def _is_resource_provider_registered(cmd, resource_provider, subscription_id=None):
    registered = None
    if not subscription_id:
        subscription_id = get_subscription_id(cmd.cli_ctx)
    try:
        providers_client = _providers_client_factory(cmd.cli_ctx, subscription_id)
        registration_state = getattr(providers_client.get(resource_provider), 'registration_state', "NotRegistered")

        registered = (registration_state and registration_state.lower() == 'registered')
    except Exception:  # pylint: disable=broad-except
        pass
    return registered


def _providers_client_factory(cli_ctx, subscription_id=None):
    return get_mgmt_service_client(cli_ctx, ResourceType.MGMT_RESOURCE_RESOURCES,
                                   subscription_id=subscription_id).providers


def _create_cost_export(subscription: str, cluster_name: str, storage_account_name: str, resource_group_name: str,
                        storage_resource_group_name: str):
    # TODO skip if exists
    mc_resource_group = _mc_resource_group(subscription=subscription, resource_group_name=resource_group_name,
                                           cluster_name=cluster_name)
    logger.info("creating cost export job for AKS cluster %s", mc_resource_group)
    cli = _cli()
    type = 'Usage'
    # TODO: 'AmortizedCost'
    args = [
        "costmanagement", "export", "create",
        "--name", cluster_name,
        "--scope", f"/subscriptions/{subscription}/resourceGroups/{mc_resource_group}",
        "--timeframe", "MonthToDate",
        "--type", type,
        "--recurrence-period", f"from={datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        "to=2200-01-01T00:00:00",
        "--recurrence", "Daily",
        "--schedule-status", "Active",
        "--storage-account-id",
        f"/subscriptions/{subscription}/resourceGroups/{storage_resource_group_name}/providers/Microsoft.Storage/storageAccounts/{storage_account_name}",
        "--storage-container", "cost",
        "--query", "'id'",
        "--subscription", subscription,
        "-o", "tsv"
    ]
    logger.info("running command: %s", " ".join(args))
    cli.invoke(args)
    logger.info("cost export created")


def _mc_resource_group(subscription: str, resource_group_name: str, cluster_name: str) -> str:
    cli = _cli()
    cli.invoke(
        ["aks", "show", "--subscription", subscription, "--resource-group", resource_group_name, "-n", cluster_name,
         "-o", "json"])
    if cli.result.exit_code != 0:
        raise Exception("Unable to get cluster resource group")
    return cli.result.result['nodeResourceGroup']


def _ensure_storage_container(subscription_id: str, resource_group_name: str, storage_account_name: str,
                                  storage_container_name: str):
    # TODO: ensure create storage uses good security practices
    logger.info("checking storage account %s, %s", storage_account_name, subscription_id)
    create_storage_args = ["storage", "account", "create",
                           "--resource-group", resource_group_name,
                           "--name", storage_account_name,
                           "--subscription", subscription_id,
                           "--allow-blob-public-access", "false"]
    _invoke(create_storage_args)  # TODO: error handling

    logger.info(f"checking storage container {storage_container_name}, {storage_account_name}")
    _invoke(["storage", "container", "create",
             "--name", storage_container_name,
             "--account-name", storage_account_name,
             "--public-access", "off",
             "--auth-mode", "login"
             ])


def _cli() -> AzCli:
    return get_default_cli()


def _invoke(args) -> AzCli:
    cli = _cli()
    try:
        cli.invoke(args)
    except BaseException as e:
        cmd = "az " + " ".join(args)
        # TODO: is it helpful enough?
        # it seems like the error message is logged inside invokation and isn't available here
        logger.error(f"An error during setup step. Check your permissions or try to run it manually:\n{cmd}")
        raise e
    if cli.result.exit_code != 0:
        cmd = "az " + " ".join(args)
        raise Exception(f"Unexpected non-zero exit code ({cli.result.exit_code}) during command execution: az {cmd}")
    return cli
