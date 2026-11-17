"""Inference math adapted from the supplied datathon implementation.
Dynamic model bundles stay inside this adapter; HTTP inputs/outputs are validated contracts.
"""

from __future__ import annotations
from typing import Any


import numpy as np
from .features import features


def predict(bundle: Any, d: Any) -> Any:
    kind = bundle["kind"]
    task = bundle["task"]
    if kind == "blend":
        p = sum(w * predict(b, d) for w, b in bundle["components"])
    elif kind == "brands":
        p = np.empty(len(d))
        for brand, model in bundle["models"].items():
            mask = d.brand.eq(brand).to_numpy()
            p[mask] = predict(model, d.loc[mask])
    elif kind == "baseline":
        p = (
            d.service_group.map(bundle["groups"]).fillna(bundle["default"]).to_numpy()
            if task == "service"
            else np.full(len(d), bundle["default"])
        )
    else:
        if bundle.get("upstream_source"):
            d = augment_upstream(d, bundle["upstream_source"])
        x, _ = features(d, bundle["feature_set"])
        for column in bundle["columns"]:
            if column not in x:
                if "__order_" not in column:
                    raise ValueError("Required prediction feature is missing")
                x[column] = 0.0
        x = x[bundle["columns"]]
        p = (
            bundle["model"].predict_proba(x)[:, 1]
            if task == "late"
            else np.asarray(bundle["model"].predict(x)).ravel()
        )
        if bundle.get("log_target"):
            p = np.expm1(p) * bundle.get("bias_correction", 1)
    if bundle.get("calibration"):
        method, cal = bundle["calibration"]
        p = (
            cal.predict_proba(
                np.log(
                    np.clip(p, 1e-7, 1 - 1e-7) / (1 - np.clip(p, 1e-7, 1 - 1e-7))
                ).reshape(-1, 1)
            )[:, 1]
            if method == "sigmoid"
            else cal.predict(p)
        )
    return np.maximum(p, 0) if task == "service" else np.clip(p, 1e-7, 1 - 1e-7)


def augment_upstream(d: Any, source: Any = None, oof: Any = None) -> Any:
    d = d.copy()
    p = np.asarray(oof) if oof is not None else predict(source, d)
    d["_pred_service"] = p
    d["prefix_pred_service"] = (
        d.groupby("route_id")._pred_service.cumsum() - d._pred_service
    )
    d["prefix_service_excess"] = d.prefix_pred_service - d.prefix_service_allowance_min
    return d
