# ==============================================================================
# Copyright 2023 Intel Corporation
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

# daal4py Model builders API

from typing import Literal, Optional

import numpy as np

import daal4py as d4p

try:
    from pandas import DataFrame
    from pandas.core.dtypes.cast import find_common_type

    pandas_is_imported = True
except (ImportError, ModuleNotFoundError):
    pandas_is_imported = False


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


class GBTDAALBaseModel:
    def __init__(self):
        self.model_type: Optional[Literal["xgboost", "catboost", "lightgbm"]] = None

    @property
    def _is_regression(self):
        return hasattr(self, "daal_model_") and isinstance(
            self.daal_model_, d4p.gbt_regression_model
        )

    def _get_params_from_lightgbm(self, params):
        self.n_classes_ = params["num_tree_per_iteration"]
        objective_fun = params["objective"]
        if self.n_classes_ <= 2:
            if "binary" in objective_fun:  # nClasses == 1
                self.n_classes_ = 2

        self.n_features_in_ = params["max_feature_idx"] + 1

    def _get_params_from_xgboost(self, params):
        self.n_classes_ = int(params["learner"]["learner_model_param"]["num_class"])
        objective_fun = params["learner"]["learner_train_param"]["objective"]
        if self.n_classes_ <= 2:
            if objective_fun in ["binary:logistic", "binary:logitraw"]:
                self.n_classes_ = 2

        self.n_features_in_ = int(params["learner"]["learner_model_param"]["num_feature"])

    def _get_params_from_catboost(self, params):
        if "class_params" in params["model_info"]:
            self.n_classes_ = len(params["model_info"]["class_params"]["class_to_label"])
        self.n_features_in_ = len(params["features_info"]["float_features"])

    def _convert_model_from_lightgbm(self, booster):
        lgbm_params = d4p.get_lightgbm_params(booster)
        self.daal_model_ = d4p.get_gbt_model_from_lightgbm(booster, lgbm_params)
        self._get_params_from_lightgbm(lgbm_params)

    def _convert_model_from_xgboost(self, booster):
        xgb_params = d4p.get_xgboost_params(booster)
        self.daal_model_ = d4p.get_gbt_model_from_xgboost(booster, xgb_params)
        self._get_params_from_xgboost(xgb_params)

    def _convert_model_from_catboost(self, booster):
        catboost_params = d4p.get_catboost_params(booster)
        self.daal_model_ = d4p.get_gbt_model_from_catboost(booster)
        self._get_params_from_catboost(catboost_params)

    def _convert_model(self, model):
        (submodule_name, class_name) = (
            model.__class__.__module__,
            model.__class__.__name__,
        )
        self_class_name = self.__class__.__name__

        # Build GBTDAALClassifier from LightGBM
        if (submodule_name, class_name) == ("lightgbm.sklearn", "LGBMClassifier"):
            if self_class_name == "GBTDAALClassifier":
                self._convert_model_from_lightgbm(model.booster_)
            else:
                raise TypeError(
                    f"Only GBTDAALClassifier can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALClassifier from XGBoost
        elif (submodule_name, class_name) == ("xgboost.sklearn", "XGBClassifier"):
            if self_class_name == "GBTDAALClassifier":
                self._convert_model_from_xgboost(model.get_booster())
            else:
                raise TypeError(
                    f"Only GBTDAALClassifier can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALClassifier from CatBoost
        elif (submodule_name, class_name) == ("catboost.core", "CatBoostClassifier"):
            if self_class_name == "GBTDAALClassifier":
                self._convert_model_from_catboost(model)
            else:
                raise TypeError(
                    f"Only GBTDAALClassifier can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALRegressor from LightGBM
        elif (submodule_name, class_name) == ("lightgbm.sklearn", "LGBMRegressor"):
            if self_class_name == "GBTDAALRegressor":
                self._convert_model_from_lightgbm(model.booster_)
            else:
                raise TypeError(
                    f"Only GBTDAALRegressor can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALRegressor from XGBoost
        elif (submodule_name, class_name) == ("xgboost.sklearn", "XGBRegressor"):
            if self_class_name == "GBTDAALRegressor":
                self._convert_model_from_xgboost(model.get_booster())
            else:
                raise TypeError(
                    f"Only GBTDAALRegressor can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALRegressor from CatBoost
        elif (submodule_name, class_name) == ("catboost.core", "CatBoostRegressor"):
            if self_class_name == "GBTDAALRegressor":
                self._convert_model_from_catboost(model)
            else:
                raise TypeError(
                    f"Only GBTDAALRegressor can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALModel from LightGBM
        elif (submodule_name, class_name) == ("lightgbm.basic", "Booster"):
            if self_class_name == "GBTDAALModel":
                self._convert_model_from_lightgbm(model)
            else:
                raise TypeError(
                    f"Only GBTDAALModel can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALModel from XGBoost
        elif (submodule_name, class_name) == ("xgboost.core", "Booster"):
            if self_class_name == "GBTDAALModel":
                self._convert_model_from_xgboost(model)
            else:
                raise TypeError(
                    f"Only GBTDAALModel can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        # Build GBTDAALModel from CatBoost
        elif (submodule_name, class_name) == ("catboost.core", "CatBoost"):
            if self_class_name == "GBTDAALModel":
                self._convert_model_from_catboost(model)
            else:
                raise TypeError(
                    f"Only GBTDAALModel can be created from\
                                 {submodule_name}.{class_name} (got {self_class_name})"
                )
        else:
            raise TypeError(f"Unknown model format {submodule_name}.{class_name}")

    def _predict_classification(self, X, fptype, resultsToEvaluate):
        if X.shape[1] != self.n_features_in_:
            raise ValueError("Shape of input is different from what was seen in `fit`")

        if not hasattr(self, "daal_model_"):
            raise ValueError(
                (
                    "The class {} instance does not have 'daal_model_' attribute set. "
                    "Call 'fit' with appropriate arguments before using this method."
                ).format(type(self).__name__)
            )

        # Prediction
        predict_algo = d4p.gbt_classification_prediction(
            fptype=fptype, nClasses=self.n_classes_, resultsToEvaluate=resultsToEvaluate
        )
        predict_result = predict_algo.compute(X, self.daal_model_)

        if resultsToEvaluate == "computeClassLabels":
            return predict_result.prediction.ravel().astype(np.int64, copy=False)
        else:
            return predict_result.probabilities

    def _predict_regression(
        self, X, fptype, pred_contribs=False, pred_interactions=False
    ):
        if X.shape[1] != self.n_features_in_:
            raise ValueError("Shape of input is different from what was seen in `fit`")

        if not hasattr(self, "daal_model_"):
            raise ValueError(
                (
                    "The class {} instance does not have 'daal_model_' attribute set. "
                    "Call 'fit' with appropriate arguments before using this method."
                ).format(type(self).__name__)
            )

        try:
            return self._predict_regression_with_results_to_compute(
                X, fptype, pred_contribs, pred_interactions
            )
        except TypeError as e:
            if "unexpected keyword argument 'resultsToCompute'" in str(e):
                if pred_contribs or pred_interactions:
                    # SHAP values requested, but not supported by this version
                    raise TypeError(
                        f"{'pred_contribs' if pred_contribs else 'pred_interactions'} not supported by this version of daalp4y"
                    ) from e
            else:
                # unknown type error
                raise

        # fallback to calculation without `resultsToCompute`
        predict_algo = d4p.gbt_regression_prediction(fptype=fptype)
        predict_result = predict_algo.compute(X, self.daal_model_)
        return predict_result.prediction.ravel()

    def _predict_regression_with_results_to_compute(
        self, X, fptype, pred_contribs=False, pred_interactions=False
    ):
        """Assume daal4py supports the resultsToCompute kwarg"""
        resultsToCompute = ""
        if pred_contribs:
            resultsToCompute = "shapContributions"
        elif pred_interactions:
            resultsToCompute = "shapInteractions"

        predict_algo = d4p.gbt_regression_prediction(
            fptype=fptype, resultsToCompute=resultsToCompute
        )
        predict_result = predict_algo.compute(X, self.daal_model_)

        if pred_contribs:
            return predict_result.prediction.ravel().reshape((-1, X.shape[1] + 1))
        elif pred_interactions:
            return predict_result.prediction.ravel().reshape(
                (-1, X.shape[1] + 1, X.shape[1] + 1)
            )
        else:
            return predict_result.prediction.ravel()


class GBTDAALModel(GBTDAALBaseModel):
    def predict(self, X, pred_contribs=False, pred_interactions=False):
        fptype = getFPType(X)
        if self._is_regression:
            return self._predict_regression(X, fptype, pred_contribs, pred_interactions)
        else:
            if pred_contribs or pred_interactions:
                raise NotImplementedError(
                    f"{'pred_contribs' if pred_contribs else 'pred_interactions'} is not implemented for classification models"
                )
            return self._predict_classification(X, fptype, "computeClassLabels")

    def predict_proba(self, X):
        fptype = getFPType(X)
        if self._is_regression:
            raise NotImplementedError("Can't predict probabilities for regression task")
        else:
            return self._predict_classification(X, fptype, "computeClassProbabilities")


def convert_model(model):
    try:
        gbm = GBTDAALModel()
        gbm._convert_model(model)
    except TypeError as err:
        if "Only GBTDAALRegressor can be created" in str(err):
            gbm = d4p.sklearn.ensemble.GBTDAALRegressor.convert_model(model)
        elif "Only GBTDAALClassifier can be created" in str(err):
            gbm = d4p.sklearn.ensemble.GBTDAALClassifier.convert_model(model)
        else:
            raise

    for type_str in ("xgboost", "lightgbm", "catboost"):
        if type_str in str(type(model)):
            gbm.model_type = type_str
            break

    return gbm
