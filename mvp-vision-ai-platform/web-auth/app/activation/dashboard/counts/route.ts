import { NextRequest } from "next/server"
import { dashboardApi, dashboardOptions, getCounts } from "../lib"

export const dynamic = "force-dynamic"

export function GET(request: NextRequest) {
  return dashboardApi(request, () => getCounts(request))
}

export function OPTIONS(request: NextRequest) {
  return dashboardOptions(request)
}
