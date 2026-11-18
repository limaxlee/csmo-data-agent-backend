import { LOCATIONS } from "../../lib/activation/products"

export async function GET() {
  return Response.json({ location: LOCATIONS })
}