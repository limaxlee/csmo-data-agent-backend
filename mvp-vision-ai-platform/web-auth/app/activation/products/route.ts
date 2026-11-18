import { PRODUCT_TYPES, PRODUCT_LABELS } from "../../lib/activation/products"

export async function GET() {
  return Response.json(PRODUCT_TYPES.map((product_type) => ({ product_type, label: PRODUCT_LABELS[product_type] })))
}
