import { NextRequest } from "next/server"
import { dashboardApi, dashboardOptions, getTrends } from "../lib"

export const dynamic = "force-dynamic"

export function GET(request: NextRequest) {
  return dashboardApi(request, () => getTrends(request))
}

export function OPTIONS(request: NextRequest) {
  return dashboardOptions(request)
}
