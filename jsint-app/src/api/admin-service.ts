import { fetchWithAuth } from './api'
import type { AdminUser } from '@/types/admin'

export interface CreateUserPayload {
  email: string
  password: string
  is_admin: boolean
}

export interface UpdateUserPayload {
  is_admin?: boolean
  status?: AdminUser['status']
  password?: string
}

export const adminService = {
  listUsers: async (): Promise<AdminUser[]> => {
    return fetchWithAuth('/api/admin/users')
  },

  createUser: async (payload: CreateUserPayload): Promise<AdminUser> => {
    return fetchWithAuth('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  },

  updateUser: async (userId: string, payload: UpdateUserPayload): Promise<AdminUser> => {
    return fetchWithAuth(`/api/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
  },

  deleteUser: async (userId: string): Promise<null> => {
    return fetchWithAuth(`/api/admin/users/${userId}`, { method: 'DELETE' })
  }
}
