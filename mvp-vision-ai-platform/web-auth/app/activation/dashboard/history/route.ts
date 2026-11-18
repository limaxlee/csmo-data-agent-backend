import { NextRequest } from "next/server"
import { dashboardApi, dashboardOptions, getHistory } from "../lib"

export const dynamic = "force-dynamic"

export function GET(request: NextRequest) {
  return dashboardApi(request, () => getHistory(request))
}

export function OPTIONS(request: NextRequest) {
  return dashboardOptions(request)
}
