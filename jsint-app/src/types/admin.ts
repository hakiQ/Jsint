export type AccountStatus = 'pending' | 'active' | 'suspended'

export interface AdminUser {
  id: string
  email: string
  first_name?: string | null
  last_name?: string | null
  status: AccountStatus
  is_admin: boolean
  created_at?: string | null
  /** How many cases this account owns. */
  investigations: number
  sketches: number
  analyses: number
}
