import { PURPOSES } from "../../lib/activation/products"

export async function GET() {
  return Response.json({ purpose: PURPOSES })
}