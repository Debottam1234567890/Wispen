const envUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
export const API_BASE_URL = envUrl.includes('onrender.com') ? envUrl.replace('http://', 'https://') : envUrl;
// export const API_BASE_URL = 'http://localhost:5000'; // FORCE LOCALHOST for debugging
