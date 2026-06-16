/**
 * CargoNavigator API Client — unified entry point.
 *
 * Every module returns { code, msg, data } shaped responses for collection
 * endpoints, or the service-specific shape documented in each module.
 *
 * Vehicle payloads use the canonical field name `total_weight` everywhere.
 *
 * Usage:
 *   import { assessRoute, getStatistics, classifyVehicle } from '@/api'
 */
export { assessRoute, compareRoutes } from './assessment'
export { generateSurvey } from './survey'
export { generatePermit, previewPermit, exportPermit } from './permit'
export {
  createOrder,
  getOrders,
  getOrder,
  updateOrderStatus,
  getActiveOrders,
  getStatistics,
} from './tracking'
export {
  getVehicleProfiles,
  createVehicleProfile,
  updateVehicleProfile,
  deleteVehicleProfile,
} from './vehicle'
export { createApplication, getApplications, getApplication, updateApplication, deleteApplication } from './application'
export { streamChat, getAgentHealth, getSessions, getSession, deleteSession } from './agent'
export { startMonitoring, getStreamUrl, stopMonitoring, getActiveSessions } from './monitor'
export { getArchive, getExportUrl } from './archive'
