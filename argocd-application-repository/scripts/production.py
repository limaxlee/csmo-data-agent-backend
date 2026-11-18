"""Validate the stage snapshot, compute lockstep SemVer releases, and promote production (#136)."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

import yaml


SEMVER_RE = r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
SEMVER_PARTS_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SEMVER_PREFIX_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:$|[-])")
CALVER_BACKEND_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}-([0-9a-f]{7,40})$")
CALVER_FRONTEND_RE = re.compile(r"^(\d{4}\.\d{2}\.\d{2})-([0-9a-f]{7,40})-stage$")
DEFAULT_GITHUB_API_URL = "https://github.sec.samsung.net/api/v3"


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def parse_semver(tag):
    match = SEMVER_PARTS_RE.fullmatch((tag or "").strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def extract_semver_prefix(tag):
    match = SEMVER_PREFIX_RE.match((tag or "").strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def next_release_version(bump="patch", existing_tags=(), override=None):
    explicit = (override or "").strip()
    if explicit:
        if not parse_semver(explicit):
            raise ValueError("version_override must match vMAJOR.MINOR.PATCH (e.g. v1.2.0)")
        return explicit
    level = (bump or "patch").strip()
    if level not in {"patch", "minor", "major"}:
        raise ValueError("version_bump must be patch, minor, or major")
    versions = [parsed for item in existing_tags if (parsed := extract_semver_prefix(str(item)))]
    if not versions:
        return "v1.0.0"
    major, minor, patch = max(versions)
    if level == "major":
        return f"v{major + 1}.0.0"
    if level == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def resolve_stage_revision(app, revision=None):
    requested = (revision or "").strip()
    if requested and not re.fullmatch(r"[0-9a-f]{40}", requested):
        raise ValueError("stage_revision must be a full Git commit SHA")
    status = app.get("status", {})
    if (status.get("sync", {}).get("status") != "Synced"
            or status.get("health", {}).get("status") != "Healthy"
            or status.get("operationState", {}).get("phase") != "Succeeded"
            or app.get("operation")):
        raise ValueError("Stage must be Synced, Healthy, with a successful completed operation")
    if any(c["type"] in {"ComparisonError", "InvalidSpecError", "SyncError"}
           for c in (status.get("conditions") or [])):
        raise ValueError("Stage has an Argo CD error condition")
    live = status["sync"].get("revisions") or [status["sync"].get("revision")]
    if not live or any(not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{40}", item)
                       for item in live):
        raise ValueError("Stage live revision must be a full Git commit SHA")
    if len(set(live)) != 1:
        raise ValueError("Requested revision is not the currently verified stage revision")
    resolved = live[0]
    if requested and resolved != requested:
        raise ValueError("Requested revision is not the currently verified stage revision")
    return resolved


def stage_snapshot(app, revision, values, version):
    resolved = resolve_stage_revision(app, revision)
    if not parse_semver(version):
        raise ValueError("Release version must match vMAJOR.MINOR.PATCH")
    backend = str(values["backend"]["tag"])
    frontend = str(values["frontend"]["tag"])

    calver_be = CALVER_BACKEND_RE.fullmatch(backend)
    if calver_be:
        backend_ref = calver_be.group(1)
    elif parse_semver(backend):
        backend_ref = backend
    else:
        raise ValueError("Stage backend must have an immutable CalVer-SHA or vX.Y.Z tag")

    calver_fe = CALVER_FRONTEND_RE.fullmatch(frontend)
    if calver_fe:
        frontend_ref = calver_fe.group(2)
    else:
        semver_fe = re.fullmatch(rf"({SEMVER_RE})-stage", frontend)
        if not semver_fe:
            raise ValueError("Expected a CalVer-SHA-stage or vX.Y.Z-stage frontend tag")
        frontend_ref = semver_fe.group(1)

    return {
        "stage_revision": resolved,
        "version": version,
        "stage_backend_tag": backend,
        "backend_ref": backend_ref,
        "frontend_ref": frontend_ref,
        "backend_tag": version,
        "frontend_tag": version,
    }


def list_semver_tags(repo_dir=None):
    raw = git("tag", "-l", "v*", cwd=repo_dir)
    return [line for line in raw.splitlines() if parse_semver(line)]


def resolve_repo_commit(repo_dir, ref):
    remotes = git("remote", cwd=repo_dir).splitlines()
    if "origin" in remotes:
        git("fetch", "--tags", "--force", "origin", cwd=repo_dir)
    if parse_semver(ref):
        commit = git("rev-parse", "--verify", f"refs/tags/{ref}^{{commit}}", cwd=repo_dir)
    else:
        commit = git("rev-parse", "--verify", f"{ref}^{{commit}}", cwd=repo_dir)
    git("merge-base", "--is-ancestor", commit, "origin/main", cwd=repo_dir)
    return commit


def ensure_tag_available(repo_dir, version, expected_commit=None, repo_label="repository"):
    if not git("tag", "-l", version, cwd=repo_dir):
        return
    if expected_commit is None:
        raise ValueError(f"Release tag {version} already exists in {repo_label}")
    tagged_commit = git("rev-parse", "--verify", f"refs/tags/{version}^{{commit}}", cwd=repo_dir)
    if tagged_commit != expected_commit:
        raise ValueError(
            f"Release tag {version} already exists in {repo_label} at {tagged_commit[:7]} "
            f"(expected {expected_commit[:7]})"
        )


def update_tags(path, backend, frontend):
    text = path.read_text()
    for component, tag in (("backend", backend), ("frontend", frontend)):
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
            raise ValueError("Invalid image tag")
        text, count = re.subn(
            rf'(?m)^({component}:\n(?:  .*\n)*?  tag: )"[^"]*"',
            lambda match: f'{match[1]}"{tag}"', text, count=1)
        if count != 1:
            raise ValueError(f"Cannot locate {component}.tag")
    path.write_text(text)


def check_release_config(stage_revision, baseline_revision):
    # Tags may change concurrently, but production settings must remain the
    # settings reviewed when this run started. Chart must match tested stage.
    git("diff", "--exit-code", stage_revision, "HEAD", "--", "charts/defect-studio")
    path = "environments/production/defect-studio.yaml"
    baseline = yaml.safe_load(git("show", f"{baseline_revision}:{path}"))
    current = yaml.safe_load(Path(path).read_text())
    for values in (baseline, current):
        for component in ("backend", "frontend"):
            values[component].pop("tag")
    if baseline != current:
        raise ValueError("Production configuration changed during the build; start a new run")


def _direct_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def check_repo_push_access(api_url, repo, token_env, opener=None):
    token = os.environ.get(token_env, "").strip()
    if not token:
        raise ValueError(f"{token_env} is required")
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/repos/{repo}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    client = opener or _direct_opener()
    with client.open(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if not (data.get("permissions") or {}).get("push"):
        raise ValueError(
            f"{token_env} lacks push permission on {repo}; "
            "grant Contents write (or repo scope) so unified release tags can be created"
        )


def publish_repo_release(repo_dir, repo, version, commit_sha, token_env,
                         api_url=None, notes="", opener=None):
    if not parse_semver(version):
        raise ValueError("Release version must match vMAJOR.MINOR.PATCH")
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise ValueError("commit_sha must be a full 40-character Git SHA")
    token = os.environ.get(token_env, "").strip()
    if not token:
        raise ValueError(f"{token_env} is required")

    remotes = git("remote", cwd=repo_dir).splitlines()
    if "origin" in remotes:
        git("fetch", "--tags", "--force", "origin", cwd=repo_dir)
    ensure_tag_available(repo_dir, version, expected_commit=commit_sha, repo_label=repo)

    git("config", "user.name", "defect-studio-ci", cwd=repo_dir)
    git("config", "user.email", "defect-studio-ci@noreply.sec.samsung.net", cwd=repo_dir)
    if not git("tag", "-l", version, cwd=repo_dir):
        git("tag", "-a", version, commit_sha, "-m", f"Release {version}", cwd=repo_dir)
        git("push", "origin", f"refs/tags/{version}", cwd=repo_dir)

    base_api = (api_url or os.environ.get("GITHUB_API_URL") or DEFAULT_GITHUB_API_URL).rstrip("/")
    payload = {
        "tag_name": version,
        "name": version,
        "generate_release_notes": True,
    }
    if notes and notes.strip():
        payload["body"] = notes.strip()
    req = urllib.request.Request(
        f"{base_api}/repos/{repo}/releases",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    client = opener or _direct_opener()
    try:
        with client.open(req, timeout=30):
            pass
    except urllib.error.HTTPError as exc:
        if exc.code != 422:
            raise


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("revision")
    snapshot.add_argument("app_json", type=Path)
    snapshot.add_argument("--bump", default="patch")
    snapshot.add_argument("--version-override", default="")
    snapshot.add_argument("--frontend-repo", type=Path, default=None)
    snapshot.add_argument("--backend-repo", type=Path, default=None)

    promote = sub.add_parser("promote")
    promote.add_argument("backend")
    promote.add_argument("frontend")

    guard = sub.add_parser("check-config")
    guard.add_argument("stage_revision")
    guard.add_argument("baseline_revision")

    access = sub.add_parser("check-access")
    access.add_argument("repo")
    access.add_argument("token_env")
    access.add_argument("--api-url", default="")

    release = sub.add_parser("publish-release")
    release.add_argument("repo_dir", type=Path)
    release.add_argument("repo")
    release.add_argument("version")
    release.add_argument("commit_sha")
    release.add_argument("token_env")
    release.add_argument("--notes", default="")
    release.add_argument("--api-url", default="")

    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            app = json.loads(args.app_json.read_text())
            revision = resolve_stage_revision(app, args.revision)
            git("merge-base", "--is-ancestor", revision, "origin/main")
            stage_values = yaml.safe_load(
                git("show", f"{revision}:environments/stage/defect-studio.yaml")
            )

            existing = list(list_semver_tags())
            prod_path = Path("environments/production/defect-studio.yaml")
            if prod_path.exists():
                prod_values = yaml.safe_load(prod_path.read_text()) or {}
                for comp in ("backend", "frontend"):
                    tag_val = (prod_values.get(comp) or {}).get("tag")
                    if tag_val:
                        existing.append(str(tag_val))

            if args.frontend_repo is not None:
                remotes = git("remote", cwd=args.frontend_repo).splitlines()
                if "origin" in remotes:
                    git("fetch", "--tags", "--force", "origin", cwd=args.frontend_repo)
                existing.extend(list_semver_tags(args.frontend_repo))
            if args.backend_repo is not None:
                remotes = git("remote", cwd=args.backend_repo).splitlines()
                if "origin" in remotes:
                    git("fetch", "--tags", "--force", "origin", cwd=args.backend_repo)
                existing.extend(list_semver_tags(args.backend_repo))

            version = next_release_version(args.bump, existing, args.version_override)
            ensure_tag_available(Path("."), version, expected_commit=None, repo_label="gitops")
            outputs = stage_snapshot(app, revision, stage_values, version)

            if args.frontend_repo is not None:
                fe_commit = resolve_repo_commit(args.frontend_repo, outputs["frontend_ref"])
                ensure_tag_available(args.frontend_repo, version,
                                     expected_commit=fe_commit, repo_label="frontend")
                outputs["frontend_commit"] = fe_commit
            if args.backend_repo is not None:
                be_commit = resolve_repo_commit(args.backend_repo, outputs["backend_ref"])
                ensure_tag_available(args.backend_repo, version,
                                     expected_commit=be_commit, repo_label="backend")
                outputs["backend_commit"] = be_commit

            with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
                for key, value in outputs.items():
                    handle.write(f"{key}={value}\n")
        elif args.command == "promote":
            update_tags(Path("environments/production/defect-studio.yaml"),
                        args.backend, args.frontend)
        elif args.command == "check-config":
            check_release_config(args.stage_revision, args.baseline_revision)
        elif args.command == "check-access":
            api_url = args.api_url or os.environ.get("GITHUB_API_URL") or DEFAULT_GITHUB_API_URL
            check_repo_push_access(api_url, args.repo, args.token_env)
        elif args.command == "publish-release":
            publish_repo_release(
                args.repo_dir,
                args.repo,
                args.version,
                args.commit_sha,
                args.token_env,
                api_url=args.api_url or None,
                notes=args.notes,
            )
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

