"""Errors with definite pre-submission outcomes for training dispatch."""


class TrainingPreparationError(RuntimeError):
    """The current preparation attempt made no Kubernetes create request."""

    def __init__(self, stage: str):
        self.stage = stage
        self.code = f"training_{stage}_failed"
        label = "S3 upload" if stage == "config_upload" else stage.replace("_", " ")
        super().__init__(f"Training configuration preparation failed: {label}")
