export interface Folder {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface UploadedFile {
  id: string;
  folder_id: string;
  filename: string;
  file_size_bytes: number;
  status: 'pending' | 'processing' | 'processed' | 'failed';
  error_message?: string;
  file_path?: string;
  created_at?: string;
  uploaded_at?: string;
  processed_at?: string;
}

export interface ColumnConfig {
  name: string;
  type: 'String' | 'Integer' | 'Float' | 'Date' | 'Boolean';
  is_primary_key: boolean;
  is_required: boolean;
}

export interface IngestionJob {
  id: string;
  name: string;
  folder_id: string;
  target_table: string;
  is_active: boolean;
  schedule_type: 'manual' | 'hourly' | 'daily' | 'cron';
  schedule_cron?: string;
  columns_config: ColumnConfig[];
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  last_run_status?: string;
}

export interface JobExecution {
  id: string;
  job_id: string;
  job_name: string;
  execution_time: string;
  execution_type: 'manual' | 'scheduled';
  file_name?: string;
  records_processed: number;
  records_inserted: number;
  records_updated: number;
  execution_status: 'Success' | 'Failed' | 'Running';
  error_details?: string;
}

export interface SnowflakeStatus {
  is_cloud?: boolean;
  is_cloud_connected?: boolean;
  mode_label: string;
  engine?: string;
  engine_type?: string;
  details?: Record<string, any>;
}

export interface SnowflakeConfig {
  id?: string;
  account?: string;
  user?: string;
  password?: string;
  warehouse?: string;
  database?: string;
  schema_name?: string;
  is_active: boolean;
}

export interface TableColumnSchema {
  name: string;
  type: string;
  is_primary_key: boolean;
  is_audit_column: boolean;
  nullable: boolean;
}

export interface TableDataResponse {
  table_name: string;
  total_records: number;
  page: number;
  page_size: number;
  columns: string[];
  records: Record<string, any>[];
  engine_mode: string;
}
