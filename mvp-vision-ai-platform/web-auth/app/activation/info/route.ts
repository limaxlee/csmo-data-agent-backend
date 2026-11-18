import { DEPARTMENTS, PRODUCT_TYPES, PRODUCT_LABELS } from "../../lib/activation/products"

export async function GET() {
  return Response.json({
    Products: PRODUCT_TYPES.map((product_type) => ({ title: PRODUCT_LABELS[product_type], value: product_type })),
    Department: DEPARTMENTS.map((department) => ({ title: department, value: department })),
  })
}
