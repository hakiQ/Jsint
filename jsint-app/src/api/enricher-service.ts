import { fetchWithAuth } from './api'
import type { Enricher } from '@/types/enricher'

export const enricherService = {
  get: async (type?: string): Promise<Enricher[]> => {
    const url = type ? `/api/enrichers?category=${type}` : '/api/enrichers'
    return fetchWithAuth(url, {
      method: 'GET'
    })
  },
  launch: async (enricherName: string, body: BodyInit): Promise<unknown> => {
    return fetchWithAuth(`/api/enrichers/${enricherName}/launch`, {
      method: 'POST',
      body: body
    })
  }
}
