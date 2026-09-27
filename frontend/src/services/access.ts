import type { User } from '../types'

const allowed: Record<string, string[]> = {
  sales: ['MANAGER','SALES_MANAGER','CASHIER'],
  purchases: ['MANAGER','PURCHASE_MANAGER'],
  warehouse: ['WAREHOUSE_MANAGER','STOREKEEPER'],
  finance: ['CHIEF_ACCOUNTANT','ACCOUNTANT'],
  hr: ['HR'],
  admin: [],
}
export function can(user: User | null, permission?: keyof typeof allowed): boolean {
  if (!user) return false
  if (!permission) return true
  if (user.is_superuser || ['SUPER_ADMIN','ADMIN','DIRECTOR'].includes(user.role)) return true
  return allowed[permission].includes(user.role)
}
