import { NextRequest } from "next/server"
import { checkDeviceKeys, dashboardApi, dashboardOptions } from "../../../lib"

export const dynamic = "force-dynamic"

export function PATCH(request: NextRequest, context: { params: { productType: string } }) {
  return dashboardApi(request, () => checkDeviceKeys(context.params.productType))
}

export function OPTIONS(request: NextRequest) {
  return dashboardOptions(request)
}
