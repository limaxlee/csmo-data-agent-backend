"""Canonical callback endpoint builders for trainer runtime jobs.

This module centralizes callback path generation used by subprocess/k8s/space
dispatch so trainer runtimes can receive explicit per-job endpoint maps via
``CALLBACK_ENDPOINTS``.
"""

from __future__ import annotations

from typing import Dict


def build_callback_endpoints(job_kind: str, job_id: int) -> Dict[str, str]:
    """Build callback endpoint map for a concrete job kind/id.

    Args:
        job_kind: One of ``training``, ``inference``, ``export``.
        job_id: Concrete job identifier for the selected kind.

    Returns:
        Mapping of callback event keys to relative API paths.

    Raises:
        ValueError: If ``job_kind`` is unsupported.
    """
    normalized_kind = str(job_kind or "").strip().lower()
    normalized_job_id = int(job_id)

    if normalized_kind == "training":
        endpoints = {
            "training_progress": f"/training/jobs/{normalized_job_id}/callback/progress",
            "training_completion": f"/training/jobs/{normalized_job_id}/callback/completion",
            "training_resource_telemetry": (
                f"/training/jobs/{normalized_job_id}/callback/resource-telemetry"
            ),
            "training_validation": f"/validation/jobs/{normalized_job_id}/results",
            "training_logs": f"/training/jobs/{normalized_job_id}/callback/logs",
            "training_logs_batch": f"/training/jobs/{normalized_job_id}/callback/logs/batch",
        }
        return endpoints

    if normalized_kind == "inference":
        return {
            "inference_started": f"/test_inference/inference/jobs/{normalized_job_id}/callback/started",
            "inference_progress": f"/test_inference/inference/jobs/{normalized_job_id}/callback/progress",
            "inference_completion": f"/test_inference/inference/jobs/{normalized_job_id}/callback/completion",
        }

    if normalized_kind == "export":
        return {
            "export_started": f"/export/jobs/{normalized_job_id}/callback/started",
            "export_completion": f"/export/jobs/{normalized_job_id}/callback/completion",
        }

    raise ValueError(f"Unsupported callback endpoint job_kind: {job_kind}")


def build_inference_runtime_config_endpoint(base_url: str, inference_job_id: int) -> str:
    """Build absolute runtime-config endpoint URL for a concrete inference job."""
    normalized_base = str(base_url or "").strip().rstrip("/")
    if not normalized_base:
        raise ValueError("base_url is required")
    return f"{normalized_base}/test_inference/inference/jobs/{int(inference_job_id)}/runtime-config"
