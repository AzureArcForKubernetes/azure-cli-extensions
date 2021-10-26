.. :changelog:

Release History
===============

0.7.1-beta.1
++++++++++++++++++
* Fix DF resource manager endpoint check
* Enable identity by default for extensions
* Use custom delete confirmation for partners
* microsoft.azureml.kubernetes: Adding a flag for AKS to AMLARC migration and set up corresponding FE helm values
* microsoft.openservicemesh: Remove version requirement and auto upgrade minor version check
* Adds -t as alternative to --cluster-type

0.6.1-beta.3
++++++++++++++++++
* Add async models to private version

0.6.1-beta.2
++++++++++++++++++
* Add microsoft.flux to private version

0.6.1-beta.1
++++++++++++++++++
* Remove sending identity for clusters in Dogfood
* Provide fix for getting tested distros for microsoft.openservicemesh
* Add location to model for identity

0.6.0-beta.1
++++++++++++++++++

* Update extension resource models to Track2

0.5.1-beta.1
++++++++++++++++++

* Fix Policy bug
* Add SSL support for AzureML
* Hotfix servicebus namespace creation for Track 2 changes
* Change resource tag from 'amlk8s' to 'Azure Arc-enabled ML' in microsoft.azureml.kubernetes
* Add compatible logic for the track 2 migration of resource dependence
* Remove pyhelm dependency from setup.py
* Remove pyhelm dependency from osm customization
* Add microsoft.openservicemesh customization to check distros
* Delete customization for partners 

0.4.0-beta.2
++++++++++++++++++

* Fix import bug

0.4.0-beta.1
++++++++++++++++++

* Release customization for microsoft.openservicemesh

0.3.1-beta.1
++++++++++++++++++

* Add provider registration to check to validations
* Only validate scoring fe settings when inference is enabled in microsoft.azureml.kubernetes

0.3.0-beta.1
++++++++++++++++++
* Release customization for microsoft.azureml.kubernetes

0.2.1-beta.3
++++++++++++++++++
* Change the tag created for the resources when creating the microsoft.azureml.kubernete extension
* Remove the add lock logic for the created resources when creating the microsoft.azureml.kubernete extension
* Add better error message for microsoft.azureml.kubernete

0.2.1-beta.2
++++++++++++++++++
* Add support for microsoft.policyinsights extension type

0.2.1-beta.1
++++++++++++++++++
* Add support for microsoft.azureml.kubernetes extension type

0.2.1
++++++++++++++++++

* Remove `k8s-extension update` until PATCH is supported
* Improved logging for overwriting extension name with default 

0.2.0
++++++++++++++++++

* Refactor for clear separation of extension-type specific customizations
* OpenServiceMesh customization.
* Fix clusterType of Microsoft.ResourceConnector resource
* Update clusterType validation to allow 'appliances'
* Update identity creation to use the appropriate parent resource's type and api-version
* Throw error if cluster type is not one of the 3 supported types
* Rename azuremonitor-containers extension type to microsoft.azuremonitor.containers
* Move CLI errors to non-deprecated error types
* Remove support for update

0.1.3
++++++++++++++++++

* Customization for microsoft.openservicemesh

0.1.2
++++++++++++++++++

* Add support for Arc Appliance cluster type

0.1.1
++++++++++++++++++
* Add support for microsoft-azure-defender extension type

0.1.0
++++++++++++++++++
* Initial release.
