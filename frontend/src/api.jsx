import axios from "axios";

const BASE_URL = `${window.location.protocol}//${window.location.hostname}`;

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const api = {
  // --- Dryer ---
  getStatus: () => apiClient.get("/api/dryer/status"),
  setStatus: (status) => apiClient.post(`/api/dryer/status/${status}`),
  getHistory: (mode) => apiClient.get("/api/dryer/history", { params: { mode } }),
  setPoint: (value) => apiClient.post(`/api/dryer/setpoint/${value}`),

  // --- Network ---
  getConnection: () => apiClient.get("/api/network"),
  setConnection: (ssid, password) => apiClient.post(`/api/network/${ssid}/${password}`),
  getConnectionStatus: () => apiClient.get("/api/network/status"),
  getconnectionG1OS: () => apiClient.get("/api/network/g1os"),
  setConnectionForget: () => apiClient.post("/api/network/forget"),

  // --- Configuration ---
  getConfigurations: () => apiClient.get("/api/config"),
  setConfiguration: (key, value) =>
    apiClient.post(
      "/config/set",
      new URLSearchParams({ key, value }).toString(),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    ),
  reloadConfigurations: () => apiClient.get("/api/config/reload"),
  getConfiguration: (key) => apiClient.get(`/api/config/${key}`),

  /** 🔄 Factory Reset Config */
  resetConfigurations: () => apiClient.post("/api/config/reset"),

  // --- Update ---
  getUpdateVersion: () => apiClient.get("/api/update/version"),
  getUpdateCheck: () => apiClient.get("/api/update/check"),
  getUpdateApply: () => apiClient.get("/api/update/apply"),

  // --- 🕒 Timezone ---
  /** Ottiene la timezone attuale dal Raspberry Pi */
  getTimezone: () => apiClient.get("/api/config/timezone"),

  /** Imposta una nuova timezone sul Raspberry Pi */
  setTimezone: (timezone) =>
    apiClient.post(
      "/api/config/timezone",
      new URLSearchParams({ timezone }).toString(),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    ),
};
