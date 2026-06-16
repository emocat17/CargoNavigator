/**
 * Road Survey API — wraps POST /survey/generate.
 */
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:9876'
const BASE = `${API}/api/v1`

/**
 * Generate a pre-trip road survey checklist.
 *
 * @param {{}} routeData        - RouteInfo fields
 * @param {{}} vehicleInfo      - { length, width, height, total_weight, … }
 * @param {{}} [bridgeAssessment] - Optional pre-computed bridge assessment
 * @returns {Promise<{code:number, msg:string, data:object}>}
 */
export const generateSurvey = async (routeData, vehicleInfo, bridgeAssessment = null) => {
  const payload = {
    route_data: routeData,
    vehicle_info: vehicleInfo,
  }
  if (bridgeAssessment) payload.bridge_assessment = bridgeAssessment

  const { data } = await axios.post(`${BASE}/survey/generate`, payload)
  return data
}
