import axios from 'axios'
import { BASE } from './index'

const URL = `${BASE}/applications`

export const createApplication = async (data) => (await axios.post(`${URL}/`, data)).data
export const getApplications = async () => (await axios.get(`${URL}/`)).data
export const getApplication = async (id) => (await axios.get(`${URL}/${id}`)).data
export const updateApplication = async (id, data) => (await axios.put(`${URL}/${id}`, data)).data
export const deleteApplication = async (id) => { await axios.delete(`${URL}/${id}`) }
