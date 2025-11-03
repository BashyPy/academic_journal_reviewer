import axios from 'axios';
import authService from './authService';

axios.interceptors.request.use(
  (config) => {
    // Prefer JWT token over API key
    const accessToken = authService.getAccessToken();
    const apiKey = authService.getApiKey();
    
    if (accessToken && !config.headers['Authorization']) {
      config.headers['Authorization'] = `Bearer ${accessToken}`;
    } else if (apiKey && !config.headers['X-API-Key']) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      authService.clearAuth();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default axios;
