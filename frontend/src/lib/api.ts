import { 
  Folder, 
  UploadedFile, 
  IngestionJob, 
  JobExecution, 
  SnowflakeStatus, 
  SnowflakeConfig, 
  TableColumnSchema, 
  TableDataResponse 
} from '../types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  // If body is not FormData, default to application/json
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const url = `${API_BASE}${endpoint}`;
  const resp = await fetch(url, { ...options, headers });

  if (!resp.ok) {
    let errMsg = `Request failed (${resp.status})`;
    try {
      const errJson = await resp.json();
      errMsg = errJson.detail || JSON.stringify(errJson);
    } catch {
      // fallback
    }
    throw new Error(errMsg);
  }

  return resp.json();
}

export const api = {
  // Folders
  getFolders: () => fetchApi<Folder[]>("/folders"),
  createFolder: (data: { name: string; description?: string }) =>
    fetchApi<Folder>("/folders", { method: "POST", body: JSON.stringify(data) }),
  deleteFolder: (folderId: string) =>
    fetchApi<{ success: boolean; message: string }>(`/folders/${folderId}`, { method: "DELETE" }),

  // Files
  getFiles: (folderId?: string, status?: string) => {
    const params = new URLSearchParams();
    if (folderId) params.append("folder_id", folderId);
    if (status) params.append("status", status);
    const qs = params.toString();
    return fetchApi<UploadedFile[]>(`/files${qs ? `?${qs}` : ""}`);
  },
  uploadFile: (folderId: string, file: File) => {
    const formData = new FormData();
    formData.append("folder_id", folderId);
    formData.append("file", file);
    return fetchApi<UploadedFile>("/files/upload", {
      method: "POST",
      body: formData,
    });
  },
  deleteFile: (fileId: string) =>
    fetchApi<{ success: boolean; message: string }>(`/files/${fileId}`, { method: "DELETE" }),

  // Jobs
  getJobs: () => fetchApi<IngestionJob[]>("/jobs"),
  getJob: (jobId: string) => fetchApi<IngestionJob>(`/jobs/${jobId}`),
  createJob: (data: Partial<IngestionJob>) =>
    fetchApi<IngestionJob>("/jobs", { method: "POST", body: JSON.stringify(data) }),
  updateJob: (jobId: string, data: Partial<IngestionJob>) =>
    fetchApi<IngestionJob>(`/jobs/${jobId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteJob: (jobId: string) =>
    fetchApi<{ success: boolean; message: string }>(`/jobs/${jobId}`, { method: "DELETE" }),
  runJob: (jobId: string) =>
    fetchApi<{ success: boolean; job_name: string; results: any[] }>(`/jobs/${jobId}/run`, {
      method: "POST",
    }),
  getJobHistory: (jobId?: string) =>
    fetchApi<JobExecution[]>(`/jobs/history${jobId ? `?job_id=${jobId}` : ""}`),

  // Database / Snowflake Ingested Data
  getDatabaseStatus: () => fetchApi<SnowflakeStatus>("/database/status"),
  getTables: () => fetchApi<{ tables: string[]; engine_mode: string }>("/database/tables"),
  getTableSchema: (tableName: string) =>
    fetchApi<{ table_name: string; columns: TableColumnSchema[]; engine_mode: string }>(
      `/database/tables/${tableName}/schema`
    ),
  getTableData: (
    tableName: string,
    params: { page?: number; page_size?: number; search?: string; sort_by?: string; sort_order?: string } = {}
  ) => {
    const q = new URLSearchParams();
    if (params.page) q.append("page", params.page.toString());
    if (params.page_size) q.append("page_size", params.page_size.toString());
    if (params.search) q.append("search", params.search);
    if (params.sort_by) q.append("sort_by", params.sort_by);
    if (params.sort_order) q.append("sort_order", params.sort_order);
    return fetchApi<TableDataResponse>(`/database/tables/${tableName}/data?${q.toString()}`);
  },

  // Snowflake Configuration
  getSnowflakeConfig: () => fetchApi<SnowflakeConfig>("/snowflake/config"),
  saveSnowflakeConfig: (data: Partial<SnowflakeConfig>) =>
    fetchApi<SnowflakeConfig>("/snowflake/config", { method: "POST", body: JSON.stringify(data) }),
  testSnowflakeConnection: (data: Partial<SnowflakeConfig>) =>
    fetchApi<{ success: boolean; message: string; version?: string }>("/snowflake/test", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
