export interface Profile {
  owner?: boolean
  first_name: string
  last_name: string
  id: string
  avatar_url?: string
  email?: string
  is_admin?: boolean
  status?: 'pending' | 'active' | 'suspended'
}
