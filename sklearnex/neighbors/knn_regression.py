# ==============================================================================
# Copyright 2021 Intel Corporation
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

import warnings

from sklearn.neighbors._ball_tree import BallTree
from sklearn.neighbors._base import NeighborsBase as sklearn_NeighborsBase
from sklearn.neighbors._kd_tree import KDTree

from daal4py.sklearn._n_jobs_support import control_n_jobs
from daal4py.sklearn._utils import sklearn_check_version

if not sklearn_check_version("1.2"):
    from sklearn.neighbors._base import _check_weights

import numpy as np
from sklearn.neighbors._base import VALID_METRICS
from sklearn.neighbors._regression import (
    KNeighborsRegressor as sklearn_KNeighborsRegressor,
)
from sklearn.neighbors._unsupervised import NearestNeighbors as sklearn_NearestNeighbors
from sklearn.utils.validation import _deprecate_positional_args, check_is_fitted

from onedal.neighbors import KNeighborsRegressor as onedal_KNeighborsRegressor
from onedal.utils import _check_array, _num_features, _num_samples

from .._device_offload import dispatch, wrap_output_data
from .common import KNeighborsDispatchingBase

if sklearn_check_version("0.24"):

    class KNeighborsRegressor_(sklearn_KNeighborsRegressor):
        if sklearn_check_version("1.2"):
            _parameter_constraints: dict = {
                **sklearn_KNeighborsRegressor._parameter_constraints
            }

        @_deprecate_positional_args
        def __init__(
            self,
            n_neighbors=5,
            *,
            weights="uniform",
            algorithm="auto",
            leaf_size=30,
            p=2,
            metric="minkowski",
            metric_params=None,
            n_jobs=None,
            **kwargs,
        ):
            super().__init__(
                n_neighbors=n_neighbors,
                algorithm=algorithm,
                leaf_size=leaf_size,
                metric=metric,
                p=p,
                metric_params=metric_params,
                n_jobs=n_jobs,
                **kwargs,
            )
            self.weights = (
                weights if sklearn_check_version("1.0") else _check_weights(weights)
            )

elif sklearn_check_version("0.22"):
    from sklearn.neighbors._base import SupervisedFloatMixin as BaseSupervisedFloatMixin

    class KNeighborsRegressor_(sklearn_KNeighborsRegressor, BaseSupervisedFloatMixin):
        @_deprecate_positional_args
        def __init__(
            self,
            n_neighbors=5,
            *,
            weights="uniform",
            algorithm="auto",
            leaf_size=30,
            p=2,
            metric="minkowski",
            metric_params=None,
            n_jobs=None,
            **kwargs,
        ):
            super().__init__(
                n_neighbors=n_neighbors,
                algorithm=algorithm,
                leaf_size=leaf_size,
                metric=metric,
                p=p,
                metric_params=metric_params,
                n_jobs=n_jobs,
                **kwargs,
            )
            self.weights = _check_weights(weights)

else:
    from sklearn.neighbors.base import SupervisedFloatMixin as BaseSupervisedFloatMixin

    class KNeighborsRegressor_(sklearn_KNeighborsRegressor, BaseSupervisedFloatMixin):
        @_deprecate_positional_args
        def __init__(
            self,
            n_neighbors=5,
            *,
            weights="uniform",
            algorithm="auto",
            leaf_size=30,
            p=2,
            metric="minkowski",
            metric_params=None,
            n_jobs=None,
            **kwargs,
        ):
            super().__init__(
                n_neighbors=n_neighbors,
                algorithm=algorithm,
                leaf_size=leaf_size,
                metric=metric,
                p=p,
                metric_params=metric_params,
                n_jobs=n_jobs,
                **kwargs,
            )
            self.weights = _check_weights(weights)


@control_n_jobs(decorated_methods=["fit", "predict", "kneighbors"])
class KNeighborsRegressor(KNeighborsRegressor_, KNeighborsDispatchingBase):
    if sklearn_check_version("1.2"):
        _parameter_constraints: dict = {**KNeighborsRegressor_._parameter_constraints}

    if sklearn_check_version("1.0"):

        def __init__(
            self,
            n_neighbors=5,
            *,
            weights="uniform",
            algorithm="auto",
            leaf_size=30,
            p=2,
            metric="minkowski",
            metric_params=None,
            n_jobs=None,
        ):
            super().__init__(
                n_neighbors=n_neighbors,
                weights=weights,
                algorithm=algorithm,
                leaf_size=leaf_size,
                metric=metric,
                p=p,
                metric_params=metric_params,
                n_jobs=n_jobs,
            )

    else:

        @_deprecate_positional_args
        def __init__(
            self,
            n_neighbors=5,
            *,
            weights="uniform",
            algorithm="auto",
            leaf_size=30,
            p=2,
            metric="minkowski",
            metric_params=None,
            n_jobs=None,
            **kwargs,
        ):
            super().__init__(
                n_neighbors=n_neighbors,
                weights=weights,
                algorithm=algorithm,
                leaf_size=leaf_size,
                metric=metric,
                p=p,
                metric_params=metric_params,
                n_jobs=n_jobs,
                **kwargs,
            )

    def fit(self, X, y):
        self._fit_validation(X, y)
        dispatch(
            self,
            "fit",
            {
                "onedal": self.__class__._onedal_fit,
                "sklearn": sklearn_KNeighborsRegressor.fit,
            },
            X,
            y,
        )
        return self

    @wrap_output_data
    def predict(self, X):
        check_is_fitted(self)
        if sklearn_check_version("1.0"):
            self._check_feature_names(X, reset=False)
        return dispatch(
            self,
            "predict",
            {
                "onedal": self.__class__._onedal_predict,
                "sklearn": sklearn_KNeighborsRegressor.predict,
            },
            X,
        )

    @wrap_output_data
    def kneighbors(self, X=None, n_neighbors=None, return_distance=True):
        check_is_fitted(self)
        if sklearn_check_version("1.0") and X is not None:
            self._check_feature_names(X, reset=False)
        return dispatch(
            self,
            "kneighbors",
            {
                "onedal": self.__class__._onedal_kneighbors,
                "sklearn": sklearn_KNeighborsRegressor.kneighbors,
            },
            X,
            n_neighbors=n_neighbors,
            return_distance=return_distance,
        )

    @wrap_output_data
    def radius_neighbors(
        self, X=None, radius=None, return_distance=True, sort_results=False
    ):
        _onedal_estimator = getattr(self, "_onedal_estimator", None)

        if (
            _onedal_estimator is not None
            or getattr(self, "_tree", 0) is None
            and self._fit_method == "kd_tree"
        ):
            if sklearn_check_version("0.24"):
                sklearn_NearestNeighbors.fit(self, self._fit_X, getattr(self, "_y", None))
            else:
                sklearn_NearestNeighbors.fit(self, self._fit_X)
        if sklearn_check_version("0.22"):
            result = sklearn_NearestNeighbors.radius_neighbors(
                self, X, radius, return_distance, sort_results
            )
        else:
            result = sklearn_NearestNeighbors.radius_neighbors(
                self, X, radius, return_distance
            )

        return result

    def _onedal_fit(self, X, y, queue=None):
        onedal_params = {
            "n_neighbors": self.n_neighbors,
            "weights": self.weights,
            "algorithm": self.algorithm,
            "metric": self.effective_metric_,
            "p": self.effective_metric_params_["p"],
        }

        try:
            requires_y = self._get_tags()["requires_y"]
        except KeyError:
            requires_y = False

        self._onedal_estimator = onedal_KNeighborsRegressor(**onedal_params)
        self._onedal_estimator.requires_y = requires_y
        self._onedal_estimator.effective_metric_ = self.effective_metric_
        self._onedal_estimator.effective_metric_params_ = self.effective_metric_params_
        self._onedal_estimator.fit(X, y, queue=queue)

        self._save_attributes()

    def _onedal_predict(self, X, queue=None):
        return self._onedal_estimator.predict(X, queue=queue)

    def _onedal_kneighbors(
        self, X=None, n_neighbors=None, return_distance=True, queue=None
    ):
        return self._onedal_estimator.kneighbors(
            X, n_neighbors, return_distance, queue=queue
        )

    def _save_attributes(self):
        self.n_features_in_ = self._onedal_estimator.n_features_in_
        self.n_samples_fit_ = self._onedal_estimator.n_samples_fit_
        self._fit_X = self._onedal_estimator._fit_X
        self._y = self._onedal_estimator._y
        self._fit_method = self._onedal_estimator._fit_method
        self._tree = self._onedal_estimator._tree
