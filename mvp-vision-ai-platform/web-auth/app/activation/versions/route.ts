import { versionsByProduct } from "../../lib/activation/products"

export async function GET() {
  return Response.json(versionsByProduct())
}
