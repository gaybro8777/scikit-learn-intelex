# ==============================================================================
# Copyright 2014 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import os
import sys
import warnings
from typing import Any, Callable, Tuple

import numpy as np
from numpy.lib.recfunctions import require_fields
from sklearn import __version__ as sklearn_version

from daal4py import _get__daal_link_version__ as dv

DaalVersionTuple = Tuple[int, str, int]

try:
    from packaging.version import Version
except ImportError:
    from distutils.version import LooseVersion as Version

import logging

try:
    from pandas import DataFrame
    from pandas.core.dtypes.cast import find_common_type

    pandas_is_imported = True
except (ImportError, ModuleNotFoundError):
    pandas_is_imported = False

try:
    from daal4py.oneapi import is_in_sycl_ctxt as is_in_ctx

    ctx_imported = True
except (ImportError, ModuleNotFoundError):
    ctx_imported = False

oneapi_is_available = "daal4py.oneapi" in sys.modules
if oneapi_is_available:
    from daal4py.oneapi import _get_device_name_sycl_ctxt


def set_idp_sklearn_verbose():
    logLevel = os.environ.get("IDP_SKLEARN_VERBOSE")
    try:
        if logLevel is not None:
            logging.basicConfig(
                stream=sys.stdout,
                format="%(levelname)s: %(message)s",
                level=logLevel.upper(),
            )
    except Exception:
        warnings.warn(
            'Unknown level "{}" for logging.\n'
            'Please, use one of "CRITICAL", "ERROR", '
            '"WARNING", "INFO", "DEBUG".'.format(logLevel)
        )


def get_daal_version() -> DaalVersionTuple:
    return int(dv()[0:4]), str(dv()[10:11]), int(dv()[4:8])


def daal_check_version(
    required_version: Tuple[Any, ...],
    _get_daal_version: Callable[[], DaalVersionTuple] = get_daal_version,
) -> bool:
    """Check daal version provided as (MAJOR, STATUS, MINOR+PATCH)

    This function also accepts a list or tuple of daal versions. It will return true if
    any version in the list/tuple is <= `_get_daal_version()`.
    """
    if isinstance(required_version[0], (list, tuple)):
        # a list of version candidates was provided, recursively check if any is <= _get_daal_version
        return any(
            map(lambda ver: daal_check_version(ver, _get_daal_version), required_version)
        )

    major_required, status_required, patch_required = required_version
    major, status, patch = _get_daal_version()

    if status != status_required:
        return False

    if major_required < major:
        return True
    if major == major_required:
        return patch_required <= patch

    return False


sklearn_versions_map = {}


def sklearn_check_version(ver):
    if ver in sklearn_versions_map.keys():
        return sklearn_versions_map[ver]
    if hasattr(Version(ver), "base_version"):
        base_sklearn_version = Version(sklearn_version).base_version
        res = bool(Version(base_sklearn_version) >= Version(ver))
    else:
        # packaging module not available
        res = bool(Version(sklearn_version) >= Version(ver))
    sklearn_versions_map[ver] = res
    return res


def parse_dtype(dt):
    if dt == np.double:
        return "double"
    if dt == np.single:
        return "float"
    raise ValueError(f"Input array has unexpected dtype = {dt}")


def getFPType(X):
    if pandas_is_imported:
        if isinstance(X, DataFrame):
            dt = find_common_type(X.dtypes.tolist())
            return parse_dtype(dt)

    dt = getattr(X, "dtype", None)
    return parse_dtype(dt)


def make2d(X):
    if np.isscalar(X):
        X = np.asarray(X)[np.newaxis, np.newaxis]
    elif isinstance(X, np.ndarray) and X.ndim == 1:
        X = X.reshape((X.size, 1))
    return X


def get_patch_message(s):
    if s == "daal":
        message = "running accelerated version on "
        if oneapi_is_available:
            dev = _get_device_name_sycl_ctxt()
            if dev == "cpu" or dev is None:
                message += "CPU"
            elif dev == "gpu":
                message += "GPU"
            else:
                raise ValueError(
                    f"Unexpected device name {dev}." " Supported types are cpu and gpu"
                )
        else:
            message += "CPU"

    elif s == "sklearn":
        message = "fallback to original Scikit-learn"
    elif s == "sklearn_after_daal":
        message = "failed to run accelerated version, fallback to original Scikit-learn"
    else:
        raise ValueError(
            f"Invalid input - expected one of 'daal','sklearn',"
            f" 'sklearn_after_daal', got {s}"
        )
    return message


def is_in_sycl_ctxt():
    if ctx_imported:
        return is_in_ctx()
    else:
        return False


def is_DataFrame(X):
    if pandas_is_imported:
        return isinstance(X, DataFrame)
    else:
        return False


def get_dtype(X):
    if pandas_is_imported:
        return find_common_type(list(X.dtypes)) if is_DataFrame(X) else X.dtype
    else:
        return getattr(X, "dtype", None)


def get_number_of_types(dataframe):
    dtypes = getattr(dataframe, "dtypes", None)
    try:
        return len(set(dtypes))
    except TypeError:
        return 1


def check_tree_nodes(tree_nodes):
    def convert_to_old_tree_nodes(tree_nodes):
        # conversion from sklearn>=1.3 tree nodes format to previous format:
        # removal of 'missing_go_to_left' field from node dtype
        new_field = "missing_go_to_left"
        new_dtype = tree_nodes.dtype
        old_dtype = np.dtype(
            [
                (key, value[0])
                for key, value in new_dtype.fields.items()
                if key != new_field
            ]
        )
        return require_fields(tree_nodes, old_dtype)

    if sklearn_check_version("1.3"):
        return tree_nodes
    else:
        return convert_to_old_tree_nodes(tree_nodes)


class PatchingConditionsChain:
    def __init__(self, scope_name):
        self.scope_name = scope_name
        self.patching_is_enabled = True
        self.messages = []
        self.logger = logging.getLogger("sklearnex")

    def _iter_conditions(self, conditions_and_messages):
        result = []
        for condition, message in conditions_and_messages:
            result.append(condition)
            if not condition:
                self.messages.append(message)
        return result

    def and_conditions(self, conditions_and_messages, conditions_merging=all):
        self.patching_is_enabled &= conditions_merging(
            self._iter_conditions(conditions_and_messages)
        )
        return self.patching_is_enabled

    def and_condition(self, condition, message):
        return self.and_conditions([(condition, message)])

    def or_conditions(self, conditions_and_messages, conditions_merging=all):
        self.patching_is_enabled |= conditions_merging(
            self._iter_conditions(conditions_and_messages)
        )
        return self.patching_is_enabled

    def write_log(self):
        if self.patching_is_enabled:
            self.logger.info(f"{self.scope_name}: {get_patch_message('daal')}")
        else:
            self.logger.debug(
                f"{self.scope_name}: debugging for the patch is enabled to track"
                " the usage of Intel® oneAPI Data Analytics Library (oneDAL)"
            )
            for message in self.messages:
                self.logger.debug(
                    f"{self.scope_name}: patching failed with cause - {message}"
                )
            self.logger.info(f"{self.scope_name}: {get_patch_message('sklearn')}")

    def get_status(self, logs=False):
        if logs:
            self.write_log()
        return self.patching_is_enabled
