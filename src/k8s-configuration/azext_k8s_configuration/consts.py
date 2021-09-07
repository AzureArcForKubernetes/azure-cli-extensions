# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long

# API VERSIONS -----------------------------------------

EXTENSION_API_VERSION = '2021-05-01-preview'
SOURCE_CONTROL_API_VERSION = '2021-03-01'
FLUXCONFIG_API_VERSION = '2021-06-01-preview'

# ERROR/HELP TEXT DEFINITIONS -----------------------------------------

KUSTOMIZATION_REQUIRED_VALUES_MISSING_ERROR = "Error! Kustomization definition is invalid, required values {} not found"
KUSTOMIZATION_REQUIRED_VALUES_MISSING_HELP = "Add the required values to the Kustomization object and try again"

REPOSITORY_REF_REQUIRED_VALUES_MISSING_ERROR = "Error! Repository reference is invalid"
REPOSITORY_REF_REQUIRED_VALUES_MISSING_HELP = "Specifying one of [--branch, --tag, --semver, --commit] is required"

REPOSITORY_REF_TOO_MAY_VALUES_ERROR = "Error! Repository reference is invalid"
REPOSITORY_REF_TOO_MAY_VALUES_HELP = "Specifying more than one repository ref argument that isn't --branch and --commit is invalid"

GIT_REPOSITORY_REQUIRED_VALUES_MISSING_ERROR = "Error! Required property '{}' was not specified for kind 'GitRepository'"
GIT_REPOSITORY_REQUIRED_VALUES_MISSING_HELP = "Add missing required property and try again"

INVALID_DURATION_ERROR = "Error! Invalid {0}."
INVALID_DURATION_HELP = "Specify a valid ISO8601 duration and try again"

INVALID_URL_ERROR = "Error! Invalid --url."
INVALID_URL_HELP = "Url must beginwith one of ['http://', 'https://', 'git@', 'ssh://']"

INVALID_KUBERNETES_NAME_LENGTH_ERROR = "Error! Invalid {0}."
INVALID_KUBERNETES_NAME_LENGTH_HELP = "Parameter {0} can be a maximum of {1} characters. Specify a shorter name and try again."

INVALID_KUBERNETES_NAME_HYPHEN_ERROR = "Error! Invalid {0}."
INVALID_KUBERNETES_NAME_HYPHEN_HELP = "Parameter {0} cannot begin or end with a hyphen."

INVALID_KUBERNETES_NAME_PERIOD_ERROR = "Error! Invalid {0}."
INVALID_KUBERNETES_NAME_PERIOD_HELP = "Parameter {0} cannot begin or end with a period."

INVALID_KUBERNETES_DNS_NAME_ERROR = "Error! Invalid {0}."
INVALID_KUBERNETES_DNS_NAME_HELP = "Parameter {0} can only contain lowercase alphanumeric characters and hyphens"

INVALID_KUBERNETES_DNS_SUBDOMAIN_NAME_ERROR = "Error! Invalid {0}."
INVALID_KUBERNETES_DNS_SUBDOMAIN_NAME_HELP = "Parameter {0} can only contain lowercase alphanumeric characters, hyphens, and periods"

DUPLICATE_KUSTOMIZATION_NAME_ERROR = "Error! Invalid kustomization list. Kustomization name '{0}' duplicated in multiple Kustomization objects"
DUPLICATE_KUSTOMIZATION_NAME_HELP = "Ensure that all Kustomization names are unique and try again"

KUSTOMIZATION_NAME_TOO_LONG_ERROR = "Error! Invalid Kustomization list. Flux configuration name '{0}' combined with kustomization name '{1}' cannot be greater than 62 characters"
KUSTOMIZATION_NAME_TOO_LONG_HELP = "Shorten the flux configuration or the kustomization name and try again"

SSH_PRIVATE_KEY_WITH_HTTP_URL_ERROR = "Error! An --ssh-private-key cannot be used with an http(s) url"
SSH_PRIVATE_KEY_WITH_HTTP_URL_HELP = "Verify the url provided is a valid ssh url and not an http(s) url"

KNOWN_HOSTS_WITH_HTTP_URL_ERROR = "Error! --ssh-known-hosts cannot be used with an http(s) url"
KNOWN_HOSTS_WITH_HTTP_URL_HELP = "Verify the url provided is a valid ssh url and not an http(s) url"

HTTPS_AUTH_WITH_SSH_URL_ERROR = "Error! https auth (--https-user and --https-key) cannot be used with a non-http(s) url"
HTTPS_AUTH_WITH_SSH_URL_HELP = "Verify the url provided is a valid http(s) url and not an ssh url"

KNOWN_HOSTS_BASE64_ENCODING_ERROR = "Error! ssh known_hosts is not a valid utf-8 base64 encoded string"
KNOWN_HOSTS_BASE64_ENCODING_HELP = "Verify that the string provided safely decodes into a valid utf-8 format"

KNOWN_HOSTS_FORMAT_ERROR = "Error! ssh known_hosts provided in wrong format"
KNOWN_HOSTS_FORMAT_HELP = "Verify that all lines in the known_hosts contents are provided in a valid sshd(8) format"

SSH_PRIVATE_KEY_ERROR = "Error! --ssh-private-key provided in invalid format"
SSH_PRIVATE_KEY_HELP = "Verify the key provided is a valid PEM-formatted key of type RSA, ECC, DSA, or Ed25519"

HTTPS_USER_KEY_MATCH_ERROR = "Error! --https-user and --https-key cannot be used separately"
HTTPS_USER_KEY_MATCH_HELP = "Try providing both --https-user and --https-key together"

KEY_FILE_READ_ERROR = "Error! Unable to read key file specified with: {0}"
KEY_FILE_READ_HELP = "Verify that the filepath specified exists and contains valid utf-8 data"

KEY_AND_FILE_TOGETHER_ERROR = "Error! Both textual key and key filepath cannot be provided"
KEY_AND_FILE_TOGETHER_HELP = "Try providing the file parameter without providing the plaintext parameter"

SCC_EXISTS_ON_CLUSTER_ERROR = "Error! SourceControlConfigurations with flux already exist on the cluster"
SCC_EXISTS_ON_CLUSTER_HELP = "Try removing all sourceControlConfigurations from the cluster before attempting to add fluxConfigurations"

HTTP_URL_NO_AUTH_WARNING = "Warning! https url is being used without https auth params, ensure the repository url provided is not a private repo"

NO_KUSTOMIZATIONS_WARNING = "Warning! No kustomizations were specified for this configuration. The specified source may not be applied to the cluster."

# PROVIDER REGISTRATION -----------------------------------------

CC_REGISTRATION_WARNING = "'Flux Configuration' cannot be used because '%s' provider has not been registered. More details for registering this provider can be found here - %s"
CC_REGISTRATION_LINK = "https://aka.ms/RegisterKubernetesConfigurationProvider"
CC_REGISTRATION_ERROR = "Unable to fetch registration state of '{0}' provider. Failed to enable 'flux configuration' feature..."
CC_PROVIDER_NAMESPACE = 'Microsoft.KubernetesConfiguration'
REGISTERED = "Registered"

FLUX_EXTENSION_TYPE = "microsoft.flux"

SSH_PRIVATE_KEY_KEY = "sshPrivateKey"
HTTPS_USER_KEY = "httpsUser"
HTTPS_KEY_KEY = "httpsKey"

DEPENDENCY_KEYS = ["dependencies", "depends_on", "dependsOn", "depends"]
SYNC_INTERVAL_KEYS = ["interval", "sync_interval", "syncInterval"]
RETRY_INTERVAL_KEYS = ["retryInterval", "retry_interval"]
TIMEOUT_KEYS = ["timeout"]
REQUIRED_KUSTOMIZATION_KEYS = {"name"}

VALID_DURATION_REGEX = r"((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?"
VALID_URL_REGEX = r"^(((http|https|ssh)://)|(git@))"

VALID_KUBERNETES_DNS_SUBDOMAIN_NAME_REGEX = r"^[a-z0-9]([\.\-a-z0-9]*[a-z0-9])?$"
VALID_KUBERNETES_DNS_NAME_REGEX = r"^[a-z0-9]([\-a-z0-9]*[a-z0-9])?$"

GIT = "git"
GIT_REPOSITORY = "GitRepository"

CONNECTED_CLUSTERS = "connectedclusters"
MANAGED_CLUSTERS = "managedclusters"
APPLIANCES = "appliances"

MANAGED_RP_NAMESPACE = "Microsoft.ContainerService"
CONNECTED_RP_NAMESPACE = "Microsoft.Kubernetes"
APPLIANCE_RP_NAMESPACE = "Microsoft.ResourceConnector"

KUBERNETES_MAX_NAME_SIZE = 63

DF_RM_ENDPOINT = 'https://api-dogfood.resources.windows-int.net/'

FLUX_EXTENSION_RELEASETRAIN = "FLUX_EXTENSION_RELEASETRAIN"
FLUX_EXTENSION_VERSION = "FLUX_EXTENSION_VERSION"
