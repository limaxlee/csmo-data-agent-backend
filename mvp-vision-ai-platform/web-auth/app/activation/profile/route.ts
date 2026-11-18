import { NextRequest } from "next/server"
import { requireActivationIdentity } from "../../lib/activation/auth"
import { activationErrorResponse } from "../../lib/activation/errors"

export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  try {
    const identity = await requireActivationIdentity(request)
    return Response.json({
      login_id: identity.loginId,
      username: identity.username,
      samsung_id: identity.loginId,
      department: identity.department,
    }, { headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    return activationErrorResponse(error)
  }
}