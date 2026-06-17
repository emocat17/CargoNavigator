import axios from 'axios'
import { BASE } from './index'

const URL = `${BASE}/vehicles`

export const getVehicleProfiles = async () => (await axios.get(`${URL}/`)).data
export const createVehicleProfile = async (p) => (await axios.post(`${URL}/`, p)).data
export const updateVehicleProfile = async (id, p) => (await axios.put(`${URL}/${id}`, p)).data
export const deleteVehicleProfile = async (id) => { await axios.delete(`${URL}/${id}`) }
