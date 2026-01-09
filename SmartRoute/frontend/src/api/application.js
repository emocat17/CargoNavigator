import axios from 'axios'

const API_URL = 'http://localhost:9876/api/v1/applications'

export const createApplication = async (data) => {
    const response = await axios.post(`${API_URL}/`, data)
    return response.data
}

export const updateApplication = async (id, data) => {
    const response = await axios.put(`${API_URL}/${id}`, data)
    return response.data
}

export const getApplication = async (id) => {
    const response = await axios.get(`${API_URL}/${id}`)
    return response.data
}
