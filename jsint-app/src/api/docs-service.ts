import { fetchWithAuth } from './api'

export interface DocChapter {
  slug: string
  title: string
  description: string | null
  category: string
  order: number
}

export interface DocDocument extends DocChapter {
  content: string
}

export const docsService = {
  // The API reads docs/ on the server; the browser only ever sees slugs.
  list: async (): Promise<DocChapter[]> => {
    return fetchWithAuth('/api/docs', {
      method: 'GET'
    })
  },
  get: async (slug: string): Promise<DocDocument> => {
    return fetchWithAuth(`/api/docs/${slug}`, {
      method: 'GET'
    })
  }
}
