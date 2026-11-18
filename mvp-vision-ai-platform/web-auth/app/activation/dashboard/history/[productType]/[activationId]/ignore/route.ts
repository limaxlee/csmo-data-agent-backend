import { NextRequest } from "next/server"
import { dashboardApi, dashboardOptions, toggleHistoryField } from "../../../../lib"

export const dynamic = "force-dynamic"

export function PATCH(
  request: NextRequest,
  context: { params: { productType: string; activationId: string } },
) {
  const { productType, activationId } = context.params
  return dashboardApi(request, () => toggleHistoryField(productType, activationId, "ignore"))
}

export function OPTIONS(request: NextRequest) {
  return dashboardOptions(request)
}
