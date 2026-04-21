import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api";

// Get auth token from localStorage
const getAuthToken = (): string | null => {
  return localStorage.getItem("access_token");
};

// Create axios instance with auth header
const createAuthenticatedClient = () => {
  const token = getAuthToken();

  return axios.create({
    baseURL: API_BASE_URL,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
};

export interface ComponentData {
  id?: number;
  s_no: string;
  parent: string;
  name: string;
  legend: string;
  suffix: string;
  object: string;
  svg?: string | File;
  png?: string | File;
  svg_url?: string;
  png_url?: string;
  grips: Array<{
    x: number;
    y: number;
    side: "top" | "bottom" | "left" | "right";
  }>;
  created_by?: number;
  created_at?: string;
}

export interface ComponentResponse {
  components: ComponentData[];
}

/**
 * Fetch all components for the authenticated user
 */
export async function fetchComponents(): Promise<ComponentData[]> {
  const client = createAuthenticatedClient();

  try {
    const response = await client.get<ComponentResponse>("/components/");

    return response.data.components || [];
  } catch (error: any) {
    // If 404 or empty, return empty array instead of error
    if (error.response?.status === 404 || error.response?.status === 401) {
      console.warn("No components found or unauthorized");

      return [];
    }
    // For other errors, rethrow
    console.error(
      "Failed to fetch components:",
      error.response?.data || error.message,
    );
    throw error;
  }
}

/**
 * Create a new component
 */
export async function createComponent(data: {
  name: string;
  parent: string;
  legend: string;
  suffix: string;
  object: string;
  svg?: File;
  png?: File;
  grips: Array<{ x: number; y: number; side: string }>;
}): Promise<ComponentData> {
  const client = createAuthenticatedClient();

  // Create FormData for file upload
  const formData = new FormData();

  // Generate a unique s_no (must be <= 10 chars)
  // Use 'U' + 7 random characters (base36) to ensure uniqueness and length < 10
  const randomSuffix = Math.random().toString(36).substring(2, 9).toUpperCase();
  const s_no = `U${randomSuffix}`;

  formData.append("s_no", s_no);
  formData.append("parent", data.parent);
  formData.append("name", data.name);
  formData.append("legend", data.legend);
  formData.append("suffix", data.suffix);
  formData.append("object", data.object);
  // Ensure grips is sent as a JSON string
  formData.append("grips", JSON.stringify(data.grips));

  if (data.svg) {
    formData.append("svg", data.svg);
  }
  if (data.png) {
    formData.append("png", data.png);
  }

  try {
    const response = await client.post<ComponentData>(
      "/components/",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      },
    );

    return response.data;
  } catch (error: any) {
    // Log the full error for debugging
    console.error(
      "Component creation failed:",
      error.response?.data || error.message,
    );
    throw error;
  }
}

/**
 * Update an existing component
 */
export async function updateComponent(
  id: number,
  data: {
    name?: string;
    parent?: string;
    legend?: string;
    suffix?: string;
    object?: string;
    svg?: File;
    png?: File;
    grips?: Array<{ x: number; y: number; side: string }>;
  },
): Promise<ComponentData> {
  const client = createAuthenticatedClient();

  const formData = new FormData();

  if (data.parent) formData.append("parent", data.parent);
  if (data.name) formData.append("name", data.name);
  if (data.legend) formData.append("legend", data.legend);
  if (data.suffix) formData.append("suffix", data.suffix);
  if (data.object) formData.append("object", data.object);
  if (data.grips) formData.append("grips", JSON.stringify(data.grips));
  if (data.svg) formData.append("svg", data.svg);
  if (data.png) formData.append("png", data.png);

  const response = await client.patch<ComponentData>(
    `/components/${id}/`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );

  return response.data;
}

/**
 * Delete a component
 */
export async function deleteComponent(id: number): Promise<void> {
  const client = createAuthenticatedClient();

  await client.delete(`/components/${id}/`);
}
