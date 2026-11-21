"""Training Manager Abstraction.

This module provides an abstract base class for training execution,
allowing seamless switching between subprocess (Tier 0), Kubernetes (Tier 1+),
and Space based on the TRAINING_MODE environment variable.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TrainingManager(ABC):
    """
    Abstract base class for training execution.

    Implementations:
    - SubprocessTrainingManager: Local subprocess execution (Tier 0)
    - KubernetesTrainingManager: K8s Job execution (Tier 1+)
    - SpaceTrainingManager: Space CLI adapter execution

    This abstraction allows the same code to work across different deployment tiers
    by simply changing the TRAINING_MODE environment variable.
    """

    @abstractmethod
    async def start_training(
        self,
        job_id: int,
        framework: str,
        model_name: str,
        dataset_s3_uri: str,
        callback_url: str,
        config: Dict[str, Any],
        snapshot_id: Optional[str] = None,
        dataset_version_hash: Optional[str] = None,
        custom_docker_image: Optional[str] = None,
        resource_profile: Optional[str] = None,
        gpu_size: Optional[str] = None,
        space_core_id: Optional[int] = None,
        space_core_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Start a training job.

        Args:
            job_id: TrainingJob ID
            framework: Framework name (ultralytics, timm, huggingface)
            model_name: Model name to train
            dataset_s3_uri: S3 URI of dataset
            callback_url: Backend API callback URL for status updates
            config: Training configuration dictionary
            snapshot_id: Dataset snapshot ID for reproducible training
            dataset_version_hash: Dataset version hash for reproducible training
            custom_docker_image: Custom Docker image URI (overrides default framework image)
            resource_profile: Training resource profile for schedulers that support it.
            gpu_size: GPU memory size for Space execution (5GB, 10GB, 20GB, 40GB, 60GB, 80GB)
            space_core_id: Space Core ID mapped from gpu_size
            space_core_count: Number of Space cores to allocate (1-4)

        Returns:
            Dict containing execution metadata (k8s_job_name, status, etc.)

        Raises:
            RuntimeError: If training fails to start
            FileNotFoundError: If required files/resources not found
        """

    @abstractmethod
    def stop_training(self, job_id: int) -> bool:
        """
        Stop a running training job.

        Args:
            job_id: TrainingJob ID

        Returns:
            True if successfully stopped, False otherwise
        """

    @abstractmethod
    def get_training_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current status of a training job.

        Args:
            job_id: TrainingJob ID

        Returns:
            Dict with status information, or None if job not found

        Example return:
            {
                "job_id": 123,
                "status": "running",  # pending, running, completed, failed
                "k8s_job_name": "training-123-abc123",
                "started_at": "2025-01-27T10:00:00Z",
            }
        """

    @abstractmethod
    async def start_inference(
        self,
        inference_job_id: int,
        training_job_id: Optional[int],
        framework: str,
        checkpoint_s3_uri: str,
        images_s3_uri: str,
        callback_url: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run inference with trained model.

        Args:
            inference_job_id: Inference job ID
            training_job_id: Original training job ID (optional)
            framework: Framework name (ultralytics, timm, huggingface)
            checkpoint_s3_uri: S3 URI to model checkpoint
            images_s3_uri: S3 URI to input images
            callback_url: Backend API callback URL
            config: Inference configuration dictionary

        Returns:
            Dict containing execution metadata

        Raises:
            RuntimeError: If inference fails to start
        """

    @abstractmethod
    async def start_export(
        self,
        export_job_id: int,
        training_job_id: int,
        framework: str,
        checkpoint_s3_uri: str,
        export_format: str,
        callback_url: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Export trained model to different format.

        Args:
            export_job_id: Export job ID
            training_job_id: Original training job ID
            framework: Framework name (ultralytics, timm, huggingface)
            checkpoint_s3_uri: S3 URI to model checkpoint
            export_format: Target format (onnx, tensorrt, coreml, tflite, etc.)
            callback_url: Backend API callback URL
            config: Export configuration dictionary

        Returns:
            Dict containing execution metadata

        Raises:
            RuntimeError: If export fails to start
        """

    @abstractmethod
    def cleanup_resources(self, job_id: int) -> None:
        """
        Clean up resources for a training job.

        This includes:
        - Temporary files
        - Running processes/pods
        - GPU allocations

        Args:
            job_id: TrainingJob ID
        """


# Singleton cache for training manager instances.
# SubprocessTrainingManager stores running processes in self.processes,
# so creating a new instance on every call loses track of them.
_manager_instances: Dict[str, "TrainingManager"] = {}


def get_training_manager(execution_target: Optional[str] = None) -> TrainingManager:
    """
    Factory function to get TrainingManager singleton.

    Each execution target ('subprocess', 'kubernetes', 'space') gets one
    shared instance so that state (e.g. running process handles) is preserved
    across start/stop calls.

    Args:
        execution_target: Override execution target. If None, falls back to settings.TRAINING_MODE.
            Valid values: 'subprocess', 'kubernetes', 'space'

    Returns:
        TrainingManager singleton instance

    Raises:
        ValueError: If execution_target/TRAINING_MODE is invalid
    """
    from app.core.config import settings

    target = (execution_target or settings.TRAINING_MODE).lower()

    if target in _manager_instances:
        return _manager_instances[target]

    if target == "subprocess":
        from app.core.training_managers.subprocess_manager import SubprocessTrainingManager
        logger.info("[TrainingManager] Using SubprocessTrainingManager (Tier 0)")
        _manager_instances[target] = SubprocessTrainingManager()

    elif target == "kubernetes":
        from app.core.training_managers.kubernetes_manager import KubernetesTrainingManager
        logger.info("[TrainingManager] Using KubernetesTrainingManager (Tier 1+)")
        _manager_instances[target] = KubernetesTrainingManager()

    elif target == "space":
        from app.core.training_managers.space_manager import SpaceTrainingManager
        logger.info("[TrainingManager] Using SpaceTrainingManager (Space CLI adapter mode)")
        _manager_instances[target] = SpaceTrainingManager()

    else:
        raise ValueError(
            f"Invalid execution target: {target}. "
            f"Expected 'subprocess', 'kubernetes', or 'space'"
        )

    return _manager_instances[target]
