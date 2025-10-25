import api from "./axios";

export const login = async (username, password) => {
  try {
    const response = await api.post("/api/token/", { username, password });

    // Save tokens in localStorage
    localStorage.setItem("access", response.data.access);
    localStorage.setItem("refresh", response.data.refresh);

    return response.data;
  } catch (error) {
    console.error("Login failed:", error.response?.data || error.message);
    throw error;
  }
};
