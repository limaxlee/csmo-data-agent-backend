import { DEPARTMENTS } from "../../lib/activation/products"

export async function GET() {
  return Response.json({ departments: DEPARTMENTS })
}

