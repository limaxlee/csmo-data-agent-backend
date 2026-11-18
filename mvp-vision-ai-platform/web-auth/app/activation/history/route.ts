import { NextRequest } from "next/server"
import { requireActivationIdentity } from "../../lib/activation/auth"
import { activationErrorResponse, ActivationError } from "../../lib/activation/errors"
import { getActivationHistory } from "../../lib/activation/service"

export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  try {
    const identity = await requireActivationIdentity(request)
    const requestedLoginId = request.nextUrl.searchParams.get("login_id")?.trim()
    const requestedProduct = request.nextUrl.searchParams.get("product_type")?.trim()
    const isAdmin = identity.systemRole === "admin"
    if (!isAdmin && requestedLoginId && requestedLoginId !== identity.loginId) {
      throw new ActivationError(403, "105", "You can only view your own activation history.")
    }
    return Response.json(await getActivationHistory({
      loginId: isAdmin ? requestedLoginId || undefined : identity.loginId,
      productType: requestedProduct || undefined,
    }), { headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    return activationErrorResponse(error)
  }
}
