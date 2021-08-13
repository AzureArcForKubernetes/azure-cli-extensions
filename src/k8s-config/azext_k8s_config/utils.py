# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import base64
import json
import re
from datetime import timedelta
from azure.cli.core.azclierror import (
    MutuallyExclusiveArgumentError,
    InvalidArgumentValueError
)
from . import consts


def get_cluster_rp(cluster_type):
    if cluster_type.lower() == consts.CONNECTED_CLUSTERS:
        return consts.CONNECTED_RP_NAMESPACE
    # Since cluster_type is an enum of only two values, if not connectedClusters, it will be managedClusters.
    return consts.MANAGED_RP_NAMESPACE


def get_data_from_key_or_file(key, filepath):
    if key and filepath:
        raise MutuallyExclusiveArgumentError(
            consts.KEY_AND_FILE_TOGETHER_ERROR,
            consts.KEY_AND_FILE_TOGETHER_HELP)
    data = ''
    if filepath:
        data = read_key_file(filepath)
    elif key:
        data = key
    return data


def read_config_settings_file(file_path):
    try:
        with open(file_path, 'r') as f:
            settings = json.load(f)
            if len(settings) == 0:
                raise Exception("File {} is empty".format(file_path))
            return settings
    except ValueError as ex:
        raise Exception("File {} is not a valid JSON file".format(file_path)) from ex


def read_key_file(path):
    try:
        with open(path, "r") as myfile:  # user passed in filename
            data_list = myfile.readlines()  # keeps newline characters intact
            data_list_len = len(data_list)
            if (data_list_len) <= 0:
                raise Exception("File provided does not contain any data")
            raw_data = ''.join(data_list)
        return to_base64(raw_data)
    except Exception as ex:
        raise InvalidArgumentValueError(
            consts.KEY_FILE_READ_ERROR.format(ex),
            consts.KEY_FILE_READ_HELP) from ex


def parse_dependencies(depends_on):
    depends_on = depends_on.strip()
    if depends_on[0] == '[':
        depends_on = depends_on[1:-1]
    return depends_on.split(',')


def get_duration(duration):
    if not duration:
        return duration
    regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
    parts = regex.match(duration)
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return int(timedelta(**time_params).total_seconds())


def from_base64(base64_str):
    return base64.b64decode(base64_str)


def to_base64(raw_data):
    bytes_data = raw_data.encode('utf-8')
    return base64.b64encode(bytes_data).decode('utf-8')


def fix_compliance_state(config):
    # If we get Compliant/NonCompliant as compliance_sate, change them before returning
    if config.compliance_status.compliance_state.lower() == 'noncompliant':
        config.compliance_status.compliance_state = 'Failed'
    elif config.compliance_status.compliance_state.lower() == 'compliant':
        config.compliance_status.compliance_state = 'Installed'

    return config


def get_parent_api_version(cluster_rp):
    if cluster_rp == 'Microsoft.Kubernetes':
        return '2020-01-01-preview'
    if cluster_rp == 'Microsoft.ResourceConnector':
        return '2020-09-15-privatepreview'
    if cluster_rp == 'Microsoft.ContainerService':
        return '2017-07-01'
    raise InvalidArgumentValueError("Error! Cluster RP '{}' is not supported"
                                    " for extension identity".format(cluster_rp))
