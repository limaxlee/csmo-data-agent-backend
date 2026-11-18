import { NextRequest, NextResponse } from "next/server"
import { isNextResponse, requireReleaseRole } from "../../../lib/releaseAuth"
import { getBucket, headObject, loadJsonObject } from "../../../lib/releaseS3"

const PREFIX = process.env.RUNNER_RELEASE_STORAGE_PREFIX || "runner-releases/windows"

// Historic variant set — CI (release-windows-platform.ps1) may still emit
// entries for retired bundles; only "dice-runner" is actually published today.
const VARIANTS = [
  "dice-runner",
  "dice-runner-api",
  "dice-runner-directml",
  "dice-runner-cpu",
  "dice-runner-cuda",
  "dice-runner-tensorrt",
  "cosmo",
  "env-ultralytics",
  "env-huggingface",
  "env-timm",
  "env-openmm",
  "env-vfm-v1",
  "env-cosmo",
]
const FIXED_FILENAMES: Record<string, string> = {
  "dice-runner": "dice-runner-windows-x86_64.msi",
  "dice-runner-api": "dice-runner-api-windows-x86_64.msi",
  "dice-runner-directml": "dice-runner-directml-windows-x86_64.msi",
  "dice-runner-cpu": "dice-runner-cpu-windows-x86_64.msi",
  "dice-runner-cuda": "dice-runner-cuda-windows-x86_64.msi",
  "dice-runner-tensorrt": "dice-runner-tensorrt-windows-x86_64.zip",
  cosmo: "dice-runner-windows-x86_64-cosmo.zip",
  "env-ultralytics": "dice-env-windows-x86_64-ultralytics.zip",
  "env-huggingface": "dice-env-windows-x86_64-huggingface.zip",
  "env-timm": "dice-env-windows-x86_64-timm.zip",
  "env-openmm": "dice-env-windows-x86_64-openmm.zip",
  "env-vfm-v1": "dice-env-windows-x86_64-vfm-v1.zip",
  "env-cosmo": "dice-env-windows-x86_64-cosmo.zip",
}
const DEFAULT_TITLES: Record<string, string> = {
  "dice-runner": "DICE Runner",
  "dice-runner-api": "DICE Runner",
  "dice-runner-directml": "DICE Runner + ONNX DirectML",
  "dice-runner-cpu": "DICE Runner + ONNX CPU",
  "dice-runner-cuda": "DICE Runner + ONNX CUDA",
  "dice-runner-tensorrt": "DICE Runner + ONNX TensorRT",
  cosmo: "DICE Runner with COSMO env",
  "env-ultralytics": "Env only - Ultralytics",
  "env-huggingface": "Env only - HuggingFace",
  "env-timm": "Env only - timm",
  "env-openmm": "Env only - OpenMMLab",
  "env-vfm-v1": "Env only - VFM v1",
  "env-cosmo": "Env only - COSMO",
}
const DEFAULT_DESCRIPTIONS: Record<string, string> = {
  "dice-runner":
    "Installs the DICE runner as a Windows service plus the desktop tray. Models and python envs are managed from the console.",
  "dice-runner-directml":
    "Installs the Windows ONNX runtime with the DirectML GPU execution provider.",
  cosmo: "Installs dice-runner plus a bundled COSMO Python env. Models must be loaded manually.",
  "env-ultralytics": "Installs only the Ultralytics runtime env for dice-runner model workers.",
  "env-huggingface":
    "Installs only the HuggingFace/Transformers runtime env for dice-runner model workers.",
  "env-timm": "Installs only the timm runtime env for dice-runner model workers.",
  "env-openmm": "Installs only the OpenMMLab runtime env for dice-runner model workers.",
  "env-vfm-v1": "Installs only the VFM v1 / YOLO-World runtime env for dice-runner model workers.",
  "env-cosmo":
    "Installs only the COSMO runtime env carrying OpenMMLab, VFM-v1-adjacent packages, and TensorRT runtime libs.",
}

export async function GET(request: NextRequest) {
  const auth = await requireReleaseRole(request)
  if (isNextResponse(auth)) return auth

  const bucket = getBucket()
  const prefix = PREFIX.replace(/^\/+|\/+$/g, "")
  const manifest = (await loadJsonObject(bucket, `${prefix}/latest/manifest.json`)) || {}
  const entries: any[] = Array.isArray(manifest.assets) ? manifest.assets : []

  const assets = []
  for (const entry of entries) {
    const variant = String(entry?.variant || "")
    if (!VARIANTS.includes(variant)) continue
    const storageKey = String(entry?.storage_key || `${prefix}/latest/${FIXED_FILENAMES[variant]}`)
    if (!storageKey) continue

    const head = await headObject(bucket, storageKey)
    if (!head) continue

    assets.push({
      platform: "windows",
      variant,
      title: String(entry.title || DEFAULT_TITLES[variant]),
      description: String(entry.description || DEFAULT_DESCRIPTIONS[variant]),
      file_name: String(
        entry.versioned_file_name || entry.file_name || FIXED_FILENAMES[variant],
      ),
      size_bytes: Number(head.ContentLength ?? entry.size_bytes ?? 0),
      sha256: String(entry.sha256 || "").toLowerCase(),
      updated_at: (head.LastModified || new Date()).toISOString(),
      category: String(entry.category || (variant.startsWith("env-") ? "env" : "runner")),
      includes_runner: Boolean(entry.includes_runner ?? !variant.startsWith("env-")),
      includes_env: Boolean(entry.includes_env ?? variant === "cosmo"),
      includes_tensorrt: Boolean(
        entry.includes_tensorrt ?? ["cosmo", "env-cosmo"].includes(variant),
      ),
      env_alias: entry.env_alias ? String(entry.env_alias) : null,
      install_kind: entry.install_kind ? String(entry.install_kind) : null,
      frameworks: Array.isArray(entry.frameworks) ? entry.frameworks : [],
    })
  }
  assets.sort((a, b) => VARIANTS.indexOf(a.variant) - VARIANTS.indexOf(b.variant))

  return NextResponse.json(
    {
      version: String(manifest.version || process.env.RUNNER_RELEASE_VERSION || "latest"),
      semantic_version: String(manifest.semantic_version || ""),
      build_version: String(manifest.windows_installer_version || ""),
      platform: "windows",
      generated_at: String(manifest.generated_at || new Date().toISOString()),
      assets,
    },
    { headers: { "Cache-Control": "no-store" } },
  )
}

