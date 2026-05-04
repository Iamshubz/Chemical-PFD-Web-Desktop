// src/services/projectApi.ts
import axios from "axios";

const API_BASE = "http://localhost:8000/api"; // default to your DRF prefix

export interface ApiProject {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  canvas_state?: {
    items: any[];
    connections: any[];
    sequence_counter: number;
  };
  // other backend fields...
}

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add JWT Authorization header if token exists (safe config.headers handling)
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>)["Authorization"] =
      `Bearer ${token}`;
  }

  return config;
});

/* --------------------- Projects API --------------------- */

/** GET /project/ */
export const fetchProjects = async (): Promise<ApiProject[]> => {
  const res = await client.get("/project/");

  // backend returns { status: "...", projects: [...] }
  return res.data?.projects ?? [];
};

/** GET /project/:id/ */
export const fetchProject = async (id: number): Promise<any> => {
  const res = await client.get(`/project/${id}/`);

  // ProjectDetailView returns full project object (possibly wrapped)
  return res.data;
};

/** POST /project/ */
export const createProject = async (
  name: string,
  description?: string | null,
): Promise<ApiProject> => {
  const res = await client.post("/project/", { name, description });

  // Your backend returns { message, project } — fallback to res.data
  return res.data?.project ?? res.data;
};

/**
 * PUT /project/:id/
 * payload should include canvas_state when saving diagram
 */
export const saveProjectCanvas = async (
  id: number,
  payload: {
    name?: string;
    description?: string | null;
    canvas_state?: {
      items: any[];
      connections: any[];
      sequence_counter: number;
    };
    // optional viewport or other fields
    viewport?: any;
  },
): Promise<any> => {
  const res = await client.put(`/project/${id}/`, payload);

  return res.data;
};

/** PUT /project/:id/ (update only meta is same endpoint) */
export const updateProjectMeta = async (
  id: number,
  payload: { name: string; description?: string | null },
): Promise<any> => {
  const res = await client.put(`/project/${id}/`, payload);

  return res.data;
};

/** DELETE /project/:id/ */
export const deleteProject = async (id: number): Promise<void> => {
  await client.delete(`/project/${id}/`);
};

/** POST /ai-generate/ */
export const generateAIDiagram = async (prompt: string, available_components?: string[]): Promise<any> => {
  const res = await client.post("/ai-generate/", { prompt, available_components });
  return res.data;
};

export default client;
