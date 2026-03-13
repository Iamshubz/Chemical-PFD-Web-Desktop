import client from "./client";

export const loginUser = async (username: string, password: string) => {
  const response = await client.post("/auth/login/", { username, password });

  if (response.data.access) {
    localStorage.setItem("access_token", response.data.access);
    localStorage.setItem("refresh_token", response.data.refresh);
    localStorage.setItem("username", username);
  }

  return response.data;
};

export const registerUser = async (
  username: string,
  email: string,
  password: string,
) => {
  const response = await client.post("/auth/register/", {
    username,
    email,
    password,
  });

  return response.data;
};

export const logoutUser = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("username");
};
