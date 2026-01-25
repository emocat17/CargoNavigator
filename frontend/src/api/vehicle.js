import axios from 'axios'

const API_URL = 'http://localhost:9876/api/v1/vehicles'

export const getVehicleProfiles = async () => {
    const response = await axios.get(`${API_URL}/`)
    return response.data
}

export const createVehicleProfile = async (profile) => {
    const response = await axios.post(`${API_URL}/`, profile)
    return response.data
}

export const updateVehicleProfile = async (id, profile) => {
    const response = await axios.put(`${API_URL}/${id}`, profile)
    return response.data
}

export const deleteVehicleProfile = async (id) => {
    await axios.delete(`${API_URL}/${id}`)
}
