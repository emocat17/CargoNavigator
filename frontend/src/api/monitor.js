/**
 * Monitor API — wraps monitor start / stop / sessions endpoints.
 */
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:9876'
const BASE = `${API}/api/v1`

/** Start monitoring for an order. */
export const startMonitoring = async (orderId, speed = null) => {
  const params = speed ? { speed } : {}
  const { data } = await axios.post(`${BASE}/monitor/start/${orderId}`, null, { params })
  return data
}

/** Get the SSE stream URL for a monitoring session. */
export const getStreamUrl = (orderId) => `${BASE}/monitor/stream/${orderId}`

/** Stop monitoring and persist data. */
export const stopMonitoring = async (orderId) => {
  const { data } = await axios.post(`${BASE}/monitor/stop/${orderId}`)
  return data
}

/** List active monitoring sessions. */
export const getActiveSessions = async () => {
  const { data } = await axios.get(`${BASE}/monitor/sessions`)
  return data
}
