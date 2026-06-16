import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:19876'
const URL = `${API}/api/v1/vehicles`

export const getVehicleProfiles = async () => (await axios.get(`${URL}/`)).data
export const createVehicleProfile = async (p) => (await axios.post(`${URL}/`, p)).data
export const updateVehicleProfile = async (id, p) => (await axios.put(`${URL}/${id}`, p)).data
export const deleteVehicleProfile = async (id) => { await axios.delete(`${URL}/${id}`) }
