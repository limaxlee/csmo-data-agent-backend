"use client"

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react"
import SiteHeader, { type SiteHeaderNavLink } from "../../components/SiteHeader"

const AUTH_BASE = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/+$/, "")
const PREVIEW_MODE = process.env.NEXT_PUBLIC_ACTIVATION_PREVIEW === "true"
const NAV_LINKS: SiteHeaderNavLink[] = [
  { label: "Defect", href: "/defect" },
  { label: "Labeler", href: "/labeler" },
  { label: "Trainer", href: "/platform" },
  { label: "Runner", href: "/runner" },
  { label: "Docs", href: "/docs/ko/guide/overview" },
  { label: "Download", href: "/downloads" },
  { label: "Activation", href: "/activation" },
]

const FALLBACK_DEPARTMENTS = ["MX", "VD", "DA", "Network", "GTR", "Etc"]
const VERSION_REQUIRED_PRODUCTS = new Set(["aligner", "runner"])
const PREVIEW_PROFILE: ActivationProfile = {
  login_id: "preview-user",
  username: "Preview User",
  samsung_id: "preview-user",
  department: "GTR",
}
const PREVIEW_PRODUCTS: ProductOption[] = [
  { product_type: "v1_trainer", label: "DICEv1" },
  { product_type: "v2_trainer", label: "DICEv2" },
  { product_type: "aligner", label: "Aligner" },
  { product_type: "runner", label: "Runner" },
  { product_type: "vora", label: "VORA" },
]
const PREVIEW_VERSIONS: Record<string, string[]> = {
  v1_trainer: ["v0.10.2"],
  v2_trainer: ["> v2.1.4", "<= v2.1.4"],
  aligner: ["> v1.8.1", "<= v1.8.1"],
  runner: ["> v1.7.0", "<= v1.7.0"],
  vora: ["v1.0.0"],
}

interface ActivationProfile {
  login_id: string
  username: string
  samsung_id: string
  department: string
}

interface ProductOption {
  product_type: string
  label: string
}

interface FormState {
  username: string
  samsung_id: string
  device_key: string
  department: string
  product_type: string
  version: string
  location: string
  detail: string
}

type FormErrors = Partial<Record<keyof FormState, string>>

async function readError(response: Response) {
  const payload = await response.json().catch(() => null)
  if (typeof payload?.message === "string") return payload.message
  if (typeof payload?.detail === "string") return payload.detail
  return `Request failed (${response.status})`
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${AUTH_BASE}${path}`, {
    ...init,
    credentials: "include",
    cache: "no-store",
    headers: {
      ...(init?.headers || {}),
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
    },
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<T>
}

function normalizeOptions(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)))
}

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value)
      return
    } catch {
      // Use the browser fallback for insecure origins or blocked clipboard access.
    }
  }
  const input = document.createElement("textarea")
  input.value = value
  input.setAttribute("readonly", "")
  input.style.position = "fixed"
  input.style.left = "-9999px"
  document.body.appendChild(input)
  input.select()
  const copied = document.execCommand("copy")
  document.body.removeChild(input)
  if (!copied) throw new Error("copy failed")
}

export default function ActivationPage() {
  const [profile, setProfile] = useState<ActivationProfile | null>(PREVIEW_MODE ? PREVIEW_PROFILE : null)
  const [checking, setChecking] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const [optionsError, setOptionsError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [products, setProducts] = useState<ProductOption[]>(PREVIEW_MODE ? PREVIEW_PRODUCTS : [])
  const [locations, setLocations] = useState<string[]>(PREVIEW_MODE ? ["Office PC", "Equipment PC"] : [])
  const [departments, setDepartments] = useState<string[]>(PREVIEW_MODE
    ? ["MX", "VD", "DA", "Network", "GTR", "SDI", "Electro-Mechanics", "Medison", "Etc"]
    : FALLBACK_DEPARTMENTS)
  const [versions, setVersions] = useState<Record<string, string[]>>(PREVIEW_MODE ? PREVIEW_VERSIONS : {})
  const [form, setForm] = useState<FormState>({
    username: PREVIEW_MODE ? PREVIEW_PROFILE.username : "",
    samsung_id: PREVIEW_MODE ? PREVIEW_PROFILE.samsung_id : "",
    device_key: "",
    department: PREVIEW_MODE ? PREVIEW_PROFILE.department : "",
    product_type: "",
    version: "",
    location: "",
    detail: "",
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [activationKey, setActivationKey] = useState("")
  const [copied, setCopied] = useState(false)

  const login = useCallback(() => {
    window.location.href = `${AUTH_BASE}/login?callbackUrl=${encodeURIComponent(window.location.href)}`
  }, [])
  const logout = useCallback(() => {
    window.location.href = `${AUTH_BASE}/logout`
  }, [])

  useEffect(() => {
    if (PREVIEW_MODE) {
      setChecking(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const session = await fetch(`${AUTH_BASE}/session`, { credentials: "include", cache: "no-store" })
        const sessionBody = session.ok ? await session.json() : null
        if (!sessionBody?.authenticated) return
        const currentProfile = await apiRequest<ActivationProfile>("/activation/profile")
        if (cancelled) return
        setProfile(currentProfile)
        setForm((previous) => ({
          ...previous,
          username: currentProfile.username || currentProfile.login_id,
          samsung_id: currentProfile.samsung_id || currentProfile.login_id,
          department: currentProfile.department || "",
        }))
      } catch (error) {
        if (!cancelled) setAuthError(error instanceof Error ? error.message : "Unable to load user information.")
      } finally {
        if (!cancelled) setChecking(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  const loadOptions = useCallback(async () => {
    if (!profile || PREVIEW_MODE) return
    setLoadingOptions(true)
    setOptionsError(null)
    try {
      const [productResponse, locationResponse, versionResponse, departmentResponse] = await Promise.all([
        apiRequest<ProductOption[]>("/activation/products"),
        apiRequest<{ location: string[] }>("/activation/location"),
        apiRequest<Record<string, string[]>>("/activation/versions"),
        apiRequest<{ departments: string[] }>("/activation/departments"),
      ])
      setProducts(productResponse)
      setLocations(normalizeOptions(locationResponse.location || []))
      setVersions(versionResponse)
      const choices = normalizeOptions([profile.department, ...(departmentResponse.departments || [])])
      setDepartments(choices.length ? choices : FALLBACK_DEPARTMENTS)
    } catch (error) {
      setOptionsError(error instanceof Error ? error.message : "Unable to load activation options.")
    } finally {
      setLoadingOptions(false)
    }
  }, [profile])

  useEffect(() => { void loadOptions() }, [loadOptions])

  const versionRequired = VERSION_REQUIRED_PRODUCTS.has(form.product_type)
  const versionOptions = useMemo(() => versions[form.product_type] || [], [form.product_type, versions])

  const updateField = (field: keyof FormState, value: string) => {
    setForm((previous) => ({ ...previous, [field]: value, ...(field === "product_type" ? { version: "" } : {}) }))
    setErrors((previous) => ({ ...previous, [field]: undefined }))
    setSubmitError(null)
    setActivationKey("")
    setCopied(false)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!profile || PREVIEW_MODE) return
    const nextErrors: FormErrors = {}
    if (!form.username.trim()) nextErrors.username = "Enter your name."
    if (!form.samsung_id.trim()) nextErrors.samsung_id = "Enter your Samsung ID."
    if (!form.department.trim()) nextErrors.department = "Select a department."
    if (!form.product_type.trim()) nextErrors.product_type = "Select a product type."
    if (!form.location.trim()) nextErrors.location = "Select a location."
    if (!form.detail.trim()) nextErrors.detail = "Enter details."
    else if (form.detail.trim().length < 6) nextErrors.detail = "Enter at least 6 characters."
    if (versionRequired && !form.version.trim()) nextErrors.version = "Select a product version."
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return

    setSubmitting(true)
    setSubmitError(null)
    setActivationKey("")
    setCopied(false)
    try {
      const { product_type: productType, ...fields } = form
      const result = await apiRequest<{ activation_key: string }>(`/activation/products/${encodeURIComponent(productType)}`, {
        method: "POST",
        body: JSON.stringify({
          ...fields,
          ...(versionRequired ? { version: form.version } : {}),
        }),
      })
      setActivationKey(result.activation_key)
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Failed to issue the activation key.")
    } finally {
      setSubmitting(false)
    }
  }

  const copyKey = async () => {
    try {
      await copyText(activationKey)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setSubmitError("Unable to copy. Select and copy the key manually.")
    }
  }

  const userName = profile?.username || profile?.login_id || null

  return (
    <main className="activation-page">
      <SiteHeader
        navLinks={NAV_LINKS}
        isAuthenticated={!PREVIEW_MODE && !!profile}
        userName={PREVIEW_MODE ? null : userName}
         ? undefined : login}
         ? undefined : logout}
        hideAuthAction={PREVIEW_MODE}
      />
      <div className="activation-container">
        <header className="activation-title">
          <div className="activation-icon" aria-hidden="true">⌘</div>
          <div>
            <h1>Activation</h1>
          </div>
        </header>

        {checking ? <section className="activation-card activation-message">Checking your sign-in…</section> : null}
        {!checking && authError ? <section className="activation-card activation-error">{authError}</section> : null}
        {!checking && !profile && !authError ? (
          <section className="activation-card activation-message">
            <h2>Sign in required</h2>
            <p>Sign in to issue an activation key.</p>
            <button className="activation-primary" type="button" >Sign In</button>
          </section>
        ) : null}
        {profile ? (
          <form className="activation-card" >
            <div className="activation-card-header">
              <div>
                <h2>Activation Request</h2>
              </div>
            </div>

            <div className="activation-fields">
              <Field label="Name" required error={errors.username}>
                <input value={form.username}  => updateField("username", event.target.value)} placeholder="Name" />
              </Field>
              <Field label="Samsung ID" required error={errors.samsung_id}>
                <input value={form.samsung_id}  => updateField("samsung_id", event.target.value)} placeholder="Samsung ID" />
              </Field>
              <Field label="Device Key">
                <input value={form.device_key}  => updateField("device_key", event.target.value)} placeholder="Device Key (Optional)" />
              </Field>
              <Field label="Department" required error={errors.department}>
                <select value={form.department}  => updateField("department", event.target.value)}>
                  <option value="">Select a department</option>
                  {departments.map((department) => <option key={department} value={department}>{department}</option>)}
                </select>
              </Field>
              <Field label="Location" required error={errors.location}>
                <select value={form.location}  => updateField("location", event.target.value)}>
                  <option value="">Select a location</option>
                  {locations.map((location) => <option key={location} value={location}>{location}</option>)}
                </select>
              </Field>
              <Field label="Product Type" required error={errors.product_type}>
                <select value={form.product_type}  => updateField("product_type", event.target.value)}>
                  <option value="">Select a product type</option>
                  {products.map((product) => <option key={product.product_type} value={product.product_type}>{product.label}</option>)}
                </select>
              </Field>
              {versionRequired ? (
                <Field label="Version" required error={errors.version}>
                  <select value={form.version}  => updateField("version", event.target.value)}>
                    <option value="">Select a version</option>
                    {versionOptions.map((version) => <option key={version} value={version}>{version}</option>)}
                  </select>
                </Field>
              ) : null}
              <Field label="Detail" required error={errors.detail} wide>
                <input value={form.detail}  => updateField("detail", event.target.value)} placeholder="Enter a reason (at least 6 characters)." />
              </Field>
            </div>

            <div className="activation-actions">
              {PREVIEW_MODE ? <p className="activation-preview-note">Preview mode: review the form options. Key issuance is disabled.</p> : null}
              {optionsError ? <p className="activation-error">{optionsError}</p> : null}
              {submitError ? <p className="activation-error">{submitError}</p> : null}
              {activationKey ? (
                <div className="activation-success" role="status">
                  <div>
                    <strong>Activation key issued.</strong>
                    <code>{activationKey}</code>
                  </div>
                  <button className="activation-secondary" type="button"  => void copyKey()}>{copied ? "Copied ✓" : "Copy Key"}</button>
                </div>
              ) : null}
              <button className="activation-primary" type="submit" disabled={PREVIEW_MODE || loadingOptions || submitting || !products.length}>
                {PREVIEW_MODE ? "Preview Mode" : submitting ? "Issuing…" : "Issue Activation Key"}
              </button>
            </div>
          </form>
        ) : null}
      </div>
    </main>
  )
}

function Field({
  label,
  required,
  error,
  wide,
  children,
}: {
  label: string
  required?: boolean
  error?: string
  wide?: boolean
  children: React.ReactNode
}) {
  return (
    <div className={`activation-field${wide ? " wide" : ""}`}>
      <label>{label}{required ? <span> *</span> : null}</label>
      {children}
      {error ? <small>{error}</small> : null}
    </div>
  )
}
