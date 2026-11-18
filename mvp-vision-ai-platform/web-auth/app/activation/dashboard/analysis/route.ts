import { NextRequest } from "next/server"
import { dashboardApi, dashboardOptions, getAnalysis } from "../lib"

export const dynamic = "force-dynamic"

export function GET(request: NextRequest) {
  return dashboardApi(request, () => getAnalysis(request))
}

export function OPTIONS(request: NextRequest) {
  return dashboardOptions(request)
}
