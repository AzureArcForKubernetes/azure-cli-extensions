# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# pylint: disable=protected-access

import argparse
from azure.cli.core.azclierror import InvalidArgumentValueError, ArgumentUsageError
from .vendored_sdks.v2021_11_01_preview.models import KustomizationDefinition
from .validators import validate_kustomization
from . import consts
from .utils import parse_dependencies, get_duration


class InternalKustomizationDefinition(KustomizationDefinition):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', "")
        super(KustomizationDefinition, self).__init__(**kwargs)


class KustomizationAddAction(argparse._AppendAction):
    def __call__(self, parser, namespace, values, option_string=None):
        validate_kustomization(values)
        dependencies = []
        sync_interval = None
        retry_interval = None
        timeout = None
        kwargs = {}
        for item in values:
            try:
                key, value = item.split('=', 1)
                if key in consts.DEPENDENCY_KEYS:
                    dependencies = parse_dependencies(value)
                elif key in consts.SYNC_INTERVAL_KEYS:
                    sync_interval = value
                elif key in consts.RETRY_INTERVAL_KEYS:
                    retry_interval = value
                elif key in consts.TIMEOUT_KEYS:
                    timeout = value
                else:
                    kwargs[key] = value
            except ValueError as ex:
                raise InvalidArgumentValueError('usage error: {} KEY=VALUE [KEY=VALUE ...]'
                                                .format(option_string)) from ex
        super().__call__(
            parser,
            namespace,
            InternalKustomizationDefinition(
                depends_on=dependencies,
                sync_interval_in_seconds=get_duration(sync_interval),
                retry_interval_in_seconds=get_duration(retry_interval),
                timeout_in_seconds=get_duration(timeout),
                **kwargs
            ),
            option_string
        )
