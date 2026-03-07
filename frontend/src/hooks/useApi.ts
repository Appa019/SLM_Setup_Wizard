import { useState, useCallback } from 'react'
import api from '../lib/api'
import type { AxiosRequestConfig } from 'axios'

interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useApi<T = unknown>() {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const request = useCallback(
    async (config: AxiosRequestConfig): Promise<T | null> => {
      setState({ data: null, loading: true, error: null })
      try {
        const res = await api.request<T>(config)
        setState({ data: res.data, loading: false, error: null })
        return res.data
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Erro desconhecido'
        setState({ data: null, loading: false, error: msg })
        return null
      }
    },
    []
  )

  return { ...state, request }
}
