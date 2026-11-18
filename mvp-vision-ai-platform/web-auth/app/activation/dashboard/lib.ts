import { NextResponse, type NextRequest } from "next/server"
import type { PoolClient, QueryResultRow } from "pg"
import { activationDb } from "../../lib/activation/database"
import { ActivationError } from "../../lib/activation/errors"
import { corsPreflight, withCors } from "../../auth-origin"

const PRODUCTS = {
  DICEv1: "activation_service_dicev1",
  DICEv2: "activation_service_dicev2",
  Runner: "activation_service_runner",
  Aligner: "activation_service_aligner",
} as const

type DashboardProduct = keyof typeof PRODUCTS
type Granularity = "year" | "month" | "day"

function productTable(value: string): { product: DashboardProduct; table: string } {
  if (!Object.prototype.hasOwnProperty.call(PRODUCTS, value)) {
    throw new ActivationError(400, "104", `Unsupported product_type: ${value}`)
  }
  const product = value as DashboardProduct
  return { product, table: PRODUCTS[product] }
}

function requiredProduct(value: string | null) {
  if (!value) throw new ActivationError(400, "104", "product_type is required")
  return productTable(value)
}

function queryBoolean(value: string | null, defaultValue = false): boolean {
  if (value === null) return defaultValue
  switch (value.toLowerCase()) {
    case "1": case "true": case "t": case "yes": case "y": case "on": return true
    case "0": case "false": case "f": case "no": case "n": case "off": return false
    default: throw new ActivationError(422, "104", "Invalid boolean query parameter")
  }
}

function dateRange(params: URLSearchParams, allActivations = false) {
  if (allActivations) return undefined
  const startDate = params.get("start_date")
  const endDate = params.get("end_date")
  if ((startDate === null) !== (endDate === null)) {
    throw new ActivationError(400, "104", "start_date and end_date must be provided together or both omitted")
  }
  if (startDate === null || endDate === null) return undefined
  const validDate = (value: string) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
    const parsed = new Date(`${value}T00:00:00.000Z`)
    return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value
  }
  if (!validDate(startDate) || !validDate(endDate)) {
    throw new ActivationError(422, "104", "Invalid date")
  }
  return { startDate, endDate }
}

function addFilters(
  clauses: string[],
  values: unknown[],
  confirmedOnly: boolean,
  range?: { startDate: string; endDate: string },
) {
  if (confirmedOnly) clauses.push("confirm IS TRUE AND ignore IS FALSE")
  if (range) {
    values.push(range.startDate)
    clauses.push(`activated_time >= $${values.length}::date`)
    values.push(range.endDate)
    clauses.push(`activated_time < ($${values.length}::date + INTERVAL '1 day')`)
  }
}

function where(clauses: string[]) {
  return clauses.length ? `WHERE ${clauses.join(" AND ")}` : ""
}

function record(row: QueryResultRow) {
  const activatedTime = row.activated_time
  return {
    id: Number(row.id),
    username: row.username,
    samsung_id: row.samsung_id,
    device_key: row.device_key,
    purpose: row.purpose,
    detail: row.detail,
    activated_time: normalizeIsoTimestamp(row.activated_time_iso, activatedTime),
    department: row.department,
    location: row.location,
    issuer: row.issuer,
    dice_version: row.dice_version ?? null,
    confirm: Boolean(row.confirm),
    ignore: Boolean(row.ignore),
  }
}

function normalizeIsoTimestamp(formatted: unknown, fallback: unknown) {
  if (typeof formatted !== "string") return fallback
  return formatted.replace(/\.(\d+)([+-]\d{2}:\d{2})$/, (_match: string, fraction: string, offset: string) => {
    const significant = fraction.replace(/0+$/, "")
    return `${significant ? `.${significant}` : ""}${offset}`
  })
}

function dateParts(value: unknown) {
  const text = String(value)
  const localDate = /^(\d{4})-(\d{2})-(\d{2})/.exec(text)
  if (localDate) {
    return { year: Number(localDate[1]), month: Number(localDate[2]), day: Number(localDate[3]) }
  }
  const date = value instanceof Date ? value : new Date(String(value))
  if (Number.isNaN(date.valueOf())) return null
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() + 1, day: date.getUTCDate() }
}

function bucketDate(value: { year: number; month: number; day: number }, granularity: Granularity) {
  if (granularity === "year") return new Date(Date.UTC(value.year, 0, 1))
  if (granularity === "month") return new Date(Date.UTC(value.year, value.month - 1, 1))
  return new Date(Date.UTC(value.year, value.month - 1, value.day))
}

function bucketLabel(value: Date, granularity: Granularity) {
  const year = value.getUTCFullYear()
  const month = String(value.getUTCMonth() + 1).padStart(2, "0")
  const day = String(value.getUTCDate()).padStart(2, "0")
  if (granularity === "year") return String(year)
  if (granularity === "month") return `${year}-${month}`
  return `${year}-${month}-${day}`
}

function nextBucket(value: Date, granularity: Granularity) {
  const next = new Date(value)
  if (granularity === "year") next.setUTCFullYear(next.getUTCFullYear() + 1)
  else if (granularity === "month") next.setUTCMonth(next.getUTCMonth() + 1)
  else next.setUTCDate(next.getUTCDate() + 1)
  return next
}

async function adminProfile(request: NextRequest) {
  const authorization = request.headers.get("authorization")
  if (!authorization || !/^Bearer\s+\S+$/i.test(authorization)) {
    throw new ActivationError(401, "101", "Not authenticated")
  }
  const base = (process.env.USER_SERVICE_API_URL || "").trim().replace(/\/+$/, "")
  if (!base) throw new ActivationError(503, "101", "User service is not configured.")

  let endpoint: URL
  try {
    endpoint = new URL(`${base}/users/me`)
  } catch {
    throw new ActivationError(503, "101", "User service is not configured.")
  }
  if (!["http:", "https:"].includes(endpoint.protocol) || endpoint.username || endpoint.password || endpoint.search || endpoint.hash) {
    throw new ActivationError(503, "101", "User service is not configured.")
  }

  let response: Response
  try {
    response = await fetch(endpoint.href, {
      headers: { Authorization: authorization },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(5_000),
    })
  } catch {
    throw new ActivationError(503, "101", "Unable to verify the current user.")
  }
  if (response.status === 401) throw new ActivationError(401, "101", "Not authenticated")
  if (response.status === 403) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === "string" ? body.detail : "Inactive user"
    throw new ActivationError(403, "105", detail)
  }
  if (response.status !== 200) throw new ActivationError(503, "101", "Unable to verify the current user.")

  const profile = await response.json().catch(() => null)
  if (!profile || typeof profile.is_active !== "boolean" || typeof profile.system_role !== "string") {
    throw new ActivationError(503, "101", "User profile is unavailable.")
  }
  if (!profile.is_active || profile.system_role.toLowerCase() !== "admin") {
    throw new ActivationError(403, "105", "Not enough permissions. Admin role required.")
  }
}

export async function dashboardApi(request: NextRequest, handler: () => Promise<unknown>) {
  try {
    await adminProfile(request)
    const result = await handler()
    return withCors(
      request,
      NextResponse.json(result, { headers: { "Cache-Control": "no-store" } }),
      "GET, PATCH, OPTIONS",
    )
  } catch (error) {
    if (error instanceof ActivationError) {
      return withCors(request, NextResponse.json({ detail: error.message }, { status: error.status }), "GET, PATCH, OPTIONS")
    }
    console.error("Dashboard activation API error:", error)
    return withCors(request, NextResponse.json({ detail: "Internal Server Error" }, { status: 500 }), "GET, PATCH, OPTIONS")
  }
}

export function dashboardOptions(request: NextRequest) {
  return corsPreflight(request, "GET, PATCH, OPTIONS")
}

export async function getCounts(request: NextRequest) {
  const params = request.nextUrl.searchParams
  const confirmedOnly = queryBoolean(params.get("confirmed_only"))
  const range = dateRange(params)
  const items = []
  for (const product of Object.keys(PRODUCTS) as DashboardProduct[]) {
    const { table } = productTable(product)
    const clauses: string[] = []
    const values: unknown[] = []
    addFilters(clauses, values, confirmedOnly, range)
    const result = await activationDb().query(
      `SELECT COUNT(id)::bigint AS count FROM ${table} ${where(clauses)}`,
      values,
    )
    items.push({ product_type: product, count: Number(result.rows[0]?.count ?? 0) })
  }
  return { items }
}

export async function getHistory(request: NextRequest) {
  const params = request.nextUrl.searchParams
  const productType = params.get("product_type")
  if (productType === null) throw new ActivationError(422, "104", "product_type is required")
  const { table } = requiredProduct(productType)
  const allActivations = queryBoolean(params.get("all_activations"))
  const confirmedOnly = queryBoolean(params.get("confirmed_only"))
  const range = dateRange(params, allActivations)
  const clauses: string[] = []
  const values: unknown[] = []
  addFilters(clauses, values, confirmedOnly, range)
  const result = await activationDb().query(
    `SELECT *, TO_CHAR(activated_time, 'YYYY-MM-DD"T"HH24:MI:SS.USOF') AS activated_time_iso FROM ${table} ${where(clauses)} ORDER BY activated_time DESC, id DESC`,
    values,
  )
  return { items: result.rows.map(record) }
}

export async function getAnalysis(request: NextRequest) {
  const params = request.nextUrl.searchParams
  const productType = params.get("product_type")
  const groupBy = params.get("group_by")
  if (productType === null || groupBy === null) {
    throw new ActivationError(422, "104", "product_type and group_by are required")
  }
  const { table } = requiredProduct(productType)
  if (groupBy !== "department" && groupBy !== "purpose" && groupBy !== "location") {
    throw new ActivationError(400, "104", "group_by must be one of: department, purpose, location")
  }
  const confirmedOnly = queryBoolean(params.get("confirmed_only"))
  const range = dateRange(params)
  const clauses: string[] = []
  const values: unknown[] = []
  addFilters(clauses, values, confirmedOnly, range)
  const result = await activationDb().query(
    `SELECT COALESCE(NULLIF(BTRIM(${groupBy}), ''), 'Unknown') AS label, COUNT(id)::bigint AS count FROM ${table} ${where(clauses)} GROUP BY label ORDER BY COUNT(id) DESC, label ASC`,
    values,
  )
  const items = result.rows.map((row) => ({ label: row.label, count: Number(row.count) }))
  return { total_count: items.reduce((sum, item) => sum + item.count, 0), items }
}

export async function getTrends(request: NextRequest) {
  const params = request.nextUrl.searchParams
  const productType = params.get("product_type")
  if (productType === null) throw new ActivationError(422, "104", "product_type is required")
  const { table } = requiredProduct(productType)
  const granularityValue = params.get("granularity") ?? "month"
  if (granularityValue !== "year" && granularityValue !== "month" && granularityValue !== "day") {
    throw new ActivationError(400, "104", "granularity must be one of: year, month, day")
  }
  const granularity: Granularity = granularityValue
  const confirmedOnly = queryBoolean(params.get("confirmed_only"))
  const range = dateRange(params)
  const clauses = ["activated_time IS NOT NULL"]
  const values: unknown[] = []
  addFilters(clauses, values, confirmedOnly, range)
  const result = await activationDb().query(
    `SELECT TO_CHAR(activated_time, 'YYYY-MM-DD"T"HH24:MI:SS.USOF') AS activated_time_iso FROM ${table} ${where(clauses)} ORDER BY activated_time ASC`,
    values,
  )
  const valuesByBucket = new Map<string, number>()
  const dates = result.rows.map((row) => dateParts(row.activated_time_iso)).filter((value) => value !== null)
  if (dates.length === 0) return { granularity, items: [] }

  for (const date of dates) {
    const key = bucketLabel(bucketDate(date, granularity), granularity)
    valuesByBucket.set(key, (valuesByBucket.get(key) ?? 0) + 1)
  }
  const start = range ? dateParts(`${range.startDate}T00:00:00.000Z`)! : dates[0]
  const end = range ? dateParts(`${range.endDate}T00:00:00.000Z`)! : dates[dates.length - 1]
  let current = bucketDate(start, granularity)
  const last = bucketDate(end, granularity)
  let cumulative = 0
  const items = []
  while (current.getTime() <= last.getTime()) {
    const label = bucketLabel(current, granularity)
    const newCount = valuesByBucket.get(label) ?? 0
    cumulative += newCount
    items.push({ label, new_count: newCount, cumulative_count: cumulative })
    current = nextBucket(current, granularity)
  }
  return { granularity, items }
}

export async function toggleHistoryField(
  productType: string,
  activationId: string,
  field: "confirm" | "ignore",
) {
  const { table } = productTable(productType)
  const id = Number(activationId)
  if (!/^-?\d+$/.test(activationId) || !Number.isSafeInteger(id)) {
    throw new ActivationError(422, "104", "Invalid activation id")
  }
  const result = await activationDb().query(
    `UPDATE ${table} SET ${field} = NOT COALESCE(${field}, FALSE) WHERE id = $1 RETURNING id, ${field}`,
    [id],
  )
  const row = result.rows[0]
  if (!row) throw new ActivationError(404, "104", "Activation not found")
  return { id: Number(row.id), field, value: Boolean(row[field]) }
}

export async function checkDeviceKeys(productType: string) {
  const { table } = productTable(productType)
  const client: PoolClient = await activationDb().connect()
  try {
    await client.query("BEGIN")
    const result = await client.query(
      `SELECT id, device_key, samsung_id, confirm FROM ${table} WHERE activated_time >= TIMESTAMPTZ '2026-01-01 00:00:00+00' ORDER BY activated_time DESC, id DESC FOR UPDATE`,
    )
    const seen = new Set<string>()
    let duplicateCount = 0
    let updatedCount = 0
    for (const row of result.rows) {
      const key = String(row.device_key ?? "").trim()
      if (!key) continue
      const pair = JSON.stringify([key, String(row.samsung_id ?? "").trim()])
      if (!seen.has(pair)) {
        seen.add(pair)
        continue
      }
      duplicateCount += 1
      if (!row.confirm) {
        await client.query(`UPDATE ${table} SET confirm = TRUE, ignore = TRUE WHERE id = $1`, [row.id])
        updatedCount += 1
      }
    }
    await client.query("COMMIT")
    return {
      product_type: productType,
      cutoff_date: "2026-01-01",
      duplicate_row_count: duplicateCount,
      updated_row_count: updatedCount,
    }
  } catch (error) {
    await client.query("ROLLBACK").catch(() => undefined)
    throw error
  } finally {
    client.release()
  }
}
