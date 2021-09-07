# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from knack.help_files import helps  # pylint: disable=unused-import

helps['k8s-configuration'] = """
    type: group
    short-summary: Commands to manage resources from Microsoft.KubernetesConfiguration.
"""

helps['k8s-configuration create'] = """
    type: command
    short-summary: Create a Kubernetes configuration.
    examples:
      - name: Create a Kubernetes configuration
        text: |-
            az k8s-configuration create --resource-group MyResourceGroup --cluster-name MyClusterName \\
            --cluster-type connectedClusters --name MyGitConfig --operator-instance-name OperatorInst01 \\
            --operator-namespace OperatorNamespace01 --operator-type flux --operator-params "'--git-readonly'" \\
            --repository-url git://github.com/fluxHowTo/flux-get-started --enable-helm-operator  \\
            --helm-operator-chart-version 1.2.0 --scope namespace --helm-operator-params '--set helm.versions=v3' \\
            --ssh-private-key '' --ssh-private-key-file '' --https-user '' --https-key '' \\
            --ssh-known-hosts '' --ssh-known-hosts-file ''
"""

helps['k8s-configuration list'] = """
    type: command
    short-summary: List Kubernetes configurations.
    examples:
      - name: List all Kubernetes configurations of a cluster
        text: |-
            az k8s-configuration list --resource-group MyResourceGroup --cluster-name MyClusterName \\
            --cluster-type connectedClusters
"""

helps['k8s-configuration delete'] = """
    type: command
    short-summary: Delete a Kubernetes configuration.
    examples:
      - name: Delete a Kubernetes configuration
        text: |-
            az k8s-configuration delete --resource-group MyResourceGroup --cluster-name MyClusterName \\
            --cluster-type connectedClusters --name MyConfigurationName
"""

helps['k8s-configuration show'] = """
    type: command
    short-summary: Show details of a Kubernetes configuration.
    examples:
      - name: Show a Kubernetes configuration
        text: |-
            az k8s-configuration show --resource-group MyResourceGroup --cluster-name MyClusterName \\
            --cluster-type connectedClusters --name MyConfigurationName
"""

helps['k8s-configuration flux'] = """
    type: group
    short-summary: Commands to manage Flux V2 Kubernetes configurations.
"""

helps['k8s-configuration flux create'] = """
    type: command
    short-summary: Create a Kubernetes Flux Configuration.
    examples:
      - name: Create a Kubernetes Flux Configuration
        text: |-
          az k8s-configuration flux create --resource-group my-resource-group --cluster-name mycluster \\
          --cluster-type connectedClusters --name myconfig --scope cluster --namespace my-namespace \\
          --kind git --url https://github.com/Azure/arc-k8s-demo --branch master --kustomization \\
          name=my-kustomization
"""

helps['k8s-configuration flux list'] = """
    type: command
    short-summary: List Kubernetes Flux Configurations.
    examples:
      - name: List all Kubernetes Flux Configurations on a cluster
        text: |-
          az k8s-configuration flux list --resource-group my-resource-group --cluster-name mycluster \\
          --cluster-type connectedClusters
"""

helps['k8s-configuration flux show'] = """
    type: command
    short-summary: Show a Kubernetes Flux Configuration.
    examples:
      - name: Show details of a Kubernetes Flux Configuration
        text: |-
          az k8s-configuration flux show --resource-group my-resource-group --cluster-name mycluster \\
          --cluster-type connectedClusters --name myconfig
"""

helps['k8s-configuration flux delete'] = """
    type: command
    short-summary: Delete a Kubernetes Flux Configuration.
    examples:
      - name: Delete an existing Kubernetes Flux Configuration
        text: |-
          az k8s-configuration flux delete --resource-group my-resource-group --cluster-name mycluster \\
          --cluster-type connectedClusters --name myconfig
"""

helps['k8s-config extension'] = """
    type: group
    short-summary: Commands to manage Kubernetes Extensions.
"""

helps['k8s-config extension create'] = """
    type: command
    short-summary: Create a Kubernetes Extension.
    examples:
      - name: Create a Kubernetes Extension
        text: |-
          az k8s-config extension create --resource-group my-resource-group \\
          --cluster-name mycluster --cluster-type connectedClusters \\
          --name myextension --extension-type microsoft.openservicemesh \\
          --scope cluster --release-train stable
"""

helps['k8s-config extension list'] = """
    type: command
    short-summary: List Kubernetes Extensions.
    examples:
      - name: List all Kubernetes Extensions on a cluster
        text: |-
          az k8s-config extension list --resource-group my-resource-group --cluster-name mycluster \\
          --cluster-type connectedClusters
"""

helps['k8s-config extension show'] = """
    type: command
    short-summary: Show a Kubernetes Extension.
    examples:
      - name: Show details of a Kubernetes Extension
        text: |-
          az k8s-config extension show --resource-group my-resource-group --cluster-name mycluster \\
          --cluster-type connectedClusters --name myextension
"""

helps['k8s-config extension delete'] = """
    type: command
    short-summary: Delete a Kubernetes Extension.
    examples:
      - name: Delete an existing Kubernetes Extension
        text: |-
          az k8s-config extension delete --resource-group my-resource-group --cluster-name mycluster \\
          --cluster-type connectedClusters --name myextension
"""
