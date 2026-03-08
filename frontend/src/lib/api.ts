import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
  timeout: 180000,  // 3 min — GPT-5.1 reasoning pode demorar
})

export const SSE_BASE = (api.defaults.baseURL ?? 'http://localhost:8000').replace(/\/$/, '')

export default api
