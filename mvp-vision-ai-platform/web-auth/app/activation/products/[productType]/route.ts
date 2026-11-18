import { NextRequest } from "next/server"
import { requireActivationIdentity } from "../../../lib/activation/auth"
import { authenticateActivationBot } from "../../../lib/activation/bot-auth"
import { activationErrorResponse } from "../../../lib/activation/errors"
import { requestActivation, type ActivationInput } from "../../../lib/activation/service"

type Context = { params: { productType: string } }
export const dynamic = "force-dynamic"

export async function POST(request: NextRequest, { params }: Context) {
  try {
    const isBot = authenticateActivationBot(request)
    const identity = isBot ? null : await requireActivationIdentity(request)
    const body = await request.json() as ActivationInput
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return Response.json({ code: "102", message: "A JSON object is required." }, { status: 400 })
    }
    return Response.json(await requestActivation({
      ...body,
      login_id: identity ? identity.loginId : body.login_id,
      issuer: isBot ? "dice-bot" : "dice-web",
    }, params.productType))
  } catch (error) {
    if (error instanceof SyntaxError) return Response.json({ code: "102", message: "A JSON object is required." }, { status: 400 })
    return activationErrorResponse(error)
  }
}
