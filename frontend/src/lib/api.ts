import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
  timeout: 180000,  // 3 min — GPT-5.4 reasoning pode demorar
})

export default api
