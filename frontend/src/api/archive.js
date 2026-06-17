/**
 * Archive API — wraps archive query and export endpoints.
 */
import axios from 'axios'
import { BASE } from './index'

/** Get the complete digital archive for an order. */
export const getArchive = async (orderId) => {
  const { data } = await axios.get(`${BASE}/archive/${orderId}`)
  return data
}

/** Get the export download URL. */
export const getExportUrl = (orderId, format = 'json') =>
  `${BASE}/archive/${orderId}/export?format=${format}`
