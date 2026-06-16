/**
 * Transport Tracking API — wraps POST / GET / PUT /tracking/orders and /tracking/statistics.
 */
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:9876'
const BASE = `${API}/api/v1`

/** Create a new tracking order. */
export const createOrder = async (orderData) => {
  const { data } = await axios.post(`${BASE}/tracking/orders`, orderData)
  return data
}

/** List tracking orders (with optional skip / limit). */
export const getOrders = async (skip = 0, limit = 100) => {
  const { data } = await axios.get(`${BASE}/tracking/orders`, { params: { skip, limit } })
  return data
}

/** Get a single order by ID. */
export const getOrder = async (orderId) => {
  const { data } = await axios.get(`${BASE}/tracking/orders/${orderId}`)
  return data
}

/** Update the status of an order. */
export const updateOrderStatus = async (orderId, status, notes = '') => {
  const { data } = await axios.put(`${BASE}/tracking/orders/${orderId}/status`, { status, notes })
  return data
}

/** Get active (in-transit) orders. */
export const getActiveOrders = async () => {
  const { data } = await axios.get(`${BASE}/tracking/orders/active`)
  return data
}

/** Get dashboard statistics. */
export const getStatistics = async () => {
  const { data } = await axios.get(`${BASE}/tracking/statistics`)
  return data
}
