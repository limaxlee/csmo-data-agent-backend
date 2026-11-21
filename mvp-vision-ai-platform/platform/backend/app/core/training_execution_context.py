"""Launch metadata shared by existing training-manager adapters."""


def execution_context_env(config):
    context = config.get("evaluation_provenance") or {}
    execution_id = context.get("execution_id")
    return {"TRAINING_EXECUTION_CONTEXT_ID": str(execution_id)} if execution_id else {}


def label_execution_manifest(manifest, config):
    """Use the same identity for direct trainers and the Space adapter Pod."""
    execution_id = execution_context_env(config).get("TRAINING_EXECUTION_CONTEXT_ID")
    if execution_id:
        for metadata in (
            manifest.setdefault("metadata", {}),
            manifest["spec"]["template"].setdefault("metadata", {}),
        ):
            metadata.setdefault("labels", {})["dice/execution-id"] = execution_id
