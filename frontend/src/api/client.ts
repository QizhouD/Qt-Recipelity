import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api/v1",
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data) {
      const data = error.response.data;
      return Promise.reject({
        code: `HTTP_${error.response.status}`,
        message: data.detail || data.message || "请求失败",
        details: data,
      });
    }
    return Promise.reject({
      code: "NETWORK_ERROR",
      message: error.message || "网络请求失败",
    });
  },
);

export default apiClient;
