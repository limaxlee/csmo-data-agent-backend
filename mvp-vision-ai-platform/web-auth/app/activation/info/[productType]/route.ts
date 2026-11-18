import { NextRequest } from "next/server"
import { activationErrorResponse } from "../../../lib/activation/errors"
import { parseProductType, versionsByProduct } from "../../../lib/activation/products"

type Context = { params: { productType: string } }

export async function GET(_request: NextRequest, { params }: Context) {
  try {
    const product = parseProductType(params.productType)
    return Response.json({ version: versionsByProduct()[product].map((value) => ({ title: value, value })) })
  } catch (error) {
    return activationErrorResponse(error)
  }
}
