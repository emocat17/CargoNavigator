/**
 * Permit Application API — wraps POST /permit/generate, POST /permit/preview, GET /permit/export.
 */
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:9876'
const BASE = `${API}/api/v1`

/**
 * Generate a complete permit application.
 *
 * @param {{}} vehicleInfo  - { length, width, height, total_weight, … }
 * @param {{}} cargoInfo    - { name, length?, width?, height?, weight? }
 * @param {{}} applicantInfo - { name?, address?, contact_person?, phone?, id_number? }
 * @param {Array<{}>} routes  - Array of route data objects
 * @returns {Promise<object>}
 */
export const generatePermit = async (vehicleInfo, cargoInfo, applicantInfo, routes) => {
  const { data } = await axios.post(`${BASE}/permit/generate`, {
    vehicle_info: vehicleInfo,
    cargo_info: cargoInfo,
    applicant_info: applicantInfo,
    routes: Array.isArray(routes) ? routes : [routes],
  })
  return data
}

/**
 * Preview a permit application (shorter text version for approver).
 *
 * @param {{}} vehicleInfo
 * @param {{}} cargoInfo
 * @param {{}} applicantInfo
 * @param {Array<{}>} routes
 * @returns {Promise<object>}
 */
export const previewPermit = async (vehicleInfo, cargoInfo, applicantInfo, routes) => {
  const { data } = await axios.post(`${BASE}/permit/preview`, {
    vehicle_info: vehicleInfo,
    cargo_info: cargoInfo,
    applicant_info: applicantInfo,
    routes: Array.isArray(routes) ? routes : [routes],
  })
  return data
}

/**
 * Export permit application data by application ID.
 *
 * @param {string} appId
 * @returns {Promise<object>}
 */
export const exportPermit = async (appId) => {
  const { data } = await axios.get(`${BASE}/permit/export/${appId}`)
  return data
}
