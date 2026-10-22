from __future__ import annotations

from typing import Any, Dict, List


def safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else num / den


def classification_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    labels = sorted(set(y_true) | set(y_pred))
    per_label = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall)
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(1 for t in y_true if t == label)}
    accuracy = safe_div(sum(1 for t, p in zip(y_true, y_pred) if t == p), len(y_true))
    macro_f1 = safe_div(sum(v["f1"] for v in per_label.values()), len(per_label)) if per_label else 0.0
    return {"accuracy": accuracy, "macro_f1": macro_f1, "per_label": per_label, "labels": labels}


def regression_metrics(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    if not y_true:
        return {"mae": 0.0, "rmse": 0.0, "mape": 0.0}
    errors = [p - t for t, p in zip(y_true, y_pred)]
    abs_errors = [abs(e) for e in errors]
    mae = sum(abs_errors) / len(abs_errors)
    rmse = (sum(e * e for e in errors) / len(errors)) ** 0.5
    mape_vals = [abs(p - t) / abs(t) for t, p in zip(y_true, y_pred) if t != 0]
    mape = sum(mape_vals) / len(mape_vals) if mape_vals else 0.0
    return {"mae": mae, "rmse": rmse, "mape": mape}
