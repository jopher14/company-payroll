import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",  // or http://localhost:8000 (must match Django CORS_ALLOWED_ORIGINS)
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // allows cookies/CSRF if you ever use session auth
});

export default api;
