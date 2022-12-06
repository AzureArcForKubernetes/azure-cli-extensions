Describe 'Cost Export Testing' {
    BeforeAll {
        $extensionType = "costexport"
        $extensionName = "costexport"

        . $PSScriptRoot/../../helper/Constants.ps1
        . $PSScriptRoot/../../helper/Helper.ps1
        $MAX_RETRY_ATTEMPTS = 30
    }

    It 'Creates the extension and checks that it onboards correctly' {
        az $Env:K8sExtensionName create -c $($ENVCONFIG.aksClusterName) -g $($ENVCONFIG.resourceGroup) --cluster-type managedClusters --extension-type $extensionType --config storageAccountId=/subscriptions/$($ENVCONFIG.subscriptionId)/resourceGroups/$($ENVCONFIG.resourceGroup)/providers/Microsoft.Storage/storageAccounts/costexporttestci2--config storageContainer=cost-export --release-train dev -n $extensionName --no-wait
        $? | Should -BeTrue

        $output = az $Env:K8sExtensionName show -c $($ENVCONFIG.aksClusterName) -g $($ENVCONFIG.resourceGroup) --cluster-type managedClusters -n $extensionName
        $? | Should -BeTrue

        $isAutoUpgradeMinorVersion = ($output | ConvertFrom-Json).autoUpgradeMinorVersion
        $isAutoUpgradeMinorVersion.ToString() -eq "True" | Should -BeTrue

        # Loop and retry until the extension installs
        $n = 0
        do
        {
            if (Has-ExtensionData $extensionName) {
                break
            }
            Start-Sleep -Seconds 10
            $n += 1
        } while ($n -le $MAX_RETRY_ATTEMPTS)
        $n | Should -BeLessOrEqual $MAX_RETRY_ATTEMPTS
    }

    It "Performs a show on the extension" {
        $output = az $Env:K8sExtensionName show -c $($ENVCONFIG.aksClusterName) -g $($ENVCONFIG.resourceGroup) --cluster-type managedClusters -n $extensionName
        $? | Should -BeTrue
        $output | Should -Not -BeNullOrEmpty
    }

    It "Lists the extensions on the cluster" {
        $output = az $Env:K8sExtensionName list -c $($ENVCONFIG.aksClusterName) -g $($ENVCONFIG.resourceGroup) --cluster-type managedClusters
        $? | Should -BeTrue

        $output | Should -Not -BeNullOrEmpty
        $extensionExists = $output | ConvertFrom-Json | Where-Object { $_.extensionType -eq $extensionType }
        $extensionExists | Should -Not -BeNullOrEmpty
    }

    It "Deletes the extension from the cluster" {
        $output = az $Env:K8sExtensionName delete -c $($ENVCONFIG.aksClusterName) -g $($ENVCONFIG.resourceGroup) --cluster-type managedClusters -n $extensionName --force
        $? | Should -BeTrue

        # Extension should not be found on the cluster
        $output = az $Env:K8sExtensionName show -c $($ENVCONFIG.aksClusterName) -g $($ENVCONFIG.resourceGroup) --cluster-type managedClusters -n $extensionName
        $? | Should -BeFalse
        $output | Should -BeNullOrEmpty
    }

    It "Performs another list after the delete" {
        $output = az $Env:K8sExtensionName list -c $($ENVCONFIG.aksClusterName) -g $($ENVCONFIG.resourceGroup) --cluster-type managedClusters
        $? | Should -BeTrue
        $output | Should -Not -BeNullOrEmpty

        $extensionExists = $output | ConvertFrom-Json | Where-Object { $_.extensionType -eq $extensionName }
        $extensionExists | Should -BeNullOrEmpty
    }
}
