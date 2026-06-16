/**
 * Route Assessment API — wraps POST /routes/assess and /routes/compare.
 *
 * Both endpoints accept { route_data, vehicle_info } where vehicle_info
 * uses the canonical field name `total_weight`.
 */
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:19876'
const BASE = `${API}/api/v1`

/**
 * Assess a single route for oversized cargo transport.
 *
 * @param {{}} routeData   - RouteInfo fields (id, route_description, distance, duration, …)
 * @param {{}} vehicleInfo - { length, width, height, total_weight, axis_weight?, axis_count?, … }
 * @returns {Promise<{code:number, msg:string, data:object}>}
 */
export const assessRoute = async (routeData, vehicleInfo) => {
  const { data } = await axios.post(`${BASE}/routes/assess`, {
    route_data: routeData,
    vehicle_info: vehicleInfo,
  })
  return data
}

/**
 * Compare multiple routes and rank by safety / feasibility.
 *
 * @param {Array<{}>} routes      - Array of route data objects
 * @param {{}}        vehicleInfo - { length, width, height, total_weight, … }
 * @returns {Promise<{code:number, msg:string, data:object}>}
 */
export const compareRoutes = async (routes, vehicleInfo) => {
  const { data } = await axios.post(`${BASE}/routes/compare`, {
    routes,
    vehicle_info: vehicleInfo,
  })
  return data
}
