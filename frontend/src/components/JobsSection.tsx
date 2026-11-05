'use client';

import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Plus, 
  Settings2, 
  Trash2, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Database, 
  Folder as FolderIcon,
  Table as TableIcon,
  Calendar,
  Layers,
  Key,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { IngestionJob, Folder, ColumnConfig } from '../types';
import { api } from '../lib/api';

interface JobsSectionProps {
  onJobExecuted?: () => void;
}

const DEFAULT_COLUMNS: ColumnConfig[] = [
  { name: 'Employee_ID', type: 'Integer', is_primary_key: true, is_required: true },
  { name: 'Employee_Name', type: 'String', is_primary_key: false, is_required: true },
  { name: 'Department', type: 'String', is_primary_key: false, is_required: true },
  { name: 'Email', type: 'String', is_primary_key: false, is_required: true },
  { name: 'Salary', type: 'Float', is_primary_key: false, is_required: true },
];

export default function JobsSection({ onJobExecuted }: JobsSectionProps) {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(false);
  const [runningJobId, setRunningJobId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingJob, setEditingJob] = useState<IngestionJob | null>(null);

  // Form Fields
  const [jobName, setJobName] = useState('');
  const [folderId, setFolderId] = useState('');
  const [targetTable, setTargetTable] = useState('');
  const [scheduleType, setScheduleType] = useState<'manual' | 'hourly' | 'daily' | 'cron'>('manual');
  const [scheduleCron, setScheduleCron] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [columns, setColumns] = useState<ColumnConfig[]>(DEFAULT_COLUMNS);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [jobsData, foldersData] = await Promise.all([
        api.getJobs(),
        api.getFolders()
      ]);
      setJobs(jobsData);
      setFolders(foldersData);
      if (foldersData.length > 0 && !folderId) {
        setFolderId(foldersData[0].id);
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to load jobs' });
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingJob(null);
    setJobName('');
    setFolderId(folders[0]?.id || '');
    setTargetTable('');
    setScheduleType('manual');
    setScheduleCron('');
    setIsActive(true);
    setColumns([
      { name: 'ID', type: 'Integer', is_primary_key: true, is_required: true },
      { name: 'Name', type: 'String', is_primary_key: false, is_required: true },
    ]);
    setShowModal(true);
  };

  const openEditModal = (job: IngestionJob) => {
    setEditingJob(job);
    setJobName(job.name);
    setFolderId(job.folder_id);
    setTargetTable(job.target_table);
    setScheduleType(job.schedule_type);
    setScheduleCron(job.schedule_cron || '');
    setIsActive(job.is_active);
    setColumns(job.columns_config || DEFAULT_COLUMNS);
    setShowModal(true);
  };

  const handleRunJob = async (job: IngestionJob) => {
    setRunningJobId(job.id);
    setMessage(null);
    try {
      const res = await api.runJob(job.id);
      const results = res.results || [];
      const hasErrors = results.some((r: any) => r.status === 'Failed');
      const totalProcessed = results.reduce((acc: number, r: any) => acc + (r.records_processed || 0), 0);

      if (hasErrors) {
        const firstErr = results.find((r: any) => r.status === 'Failed');
        setMessage({
          type: 'error',
          text: `Job "${job.name}" encountered validation error on "${firstErr.file_name}": ${firstErr.error}. File retained for correction.`
        });
      } else {
        setMessage({
          type: 'success',
          text: `Job "${job.name}" executed successfully! Ingested ${totalProcessed} record(s) into table ${job.target_table}. Processed files removed.`
        });
      }

      await loadData();
      if (onJobExecuted) onJobExecuted();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Job execution failed' });
    } finally {
      setRunningJobId(null);
    }
  };

  const handleDeleteJob = async (job: IngestionJob) => {
    if (!confirm(`Are you sure you want to delete job "${job.name}"?`)) return;
    try {
      await api.deleteJob(job.id);
      setJobs(jobs.filter(j => j.id !== job.id));
      setMessage({ type: 'success', text: `Job "${job.name}" deleted` });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to delete job' });
    }
  };

  const handleToggleActive = async (job: IngestionJob) => {
    try {
      const updated = await api.updateJob(job.id, { is_active: !job.is_active });
      setJobs(jobs.map(j => j.id === job.id ? updated : j));
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to toggle job status' });
    }
  };

  // Column Config Handlers
  const handleAddColumn = () => {
    setColumns([
      ...columns,
      { name: '', type: 'String', is_primary_key: false, is_required: true }
    ]);
  };

  const handleRemoveColumn = (index: number) => {
    if (columns.length <= 1) {
      alert("A job must have at least one business column");
      return;
    }
    setColumns(columns.filter((_, i) => i !== index));
  };

  const handleColumnChange = (index: number, field: keyof ColumnConfig, value: any) => {
    const updated = [...columns];
    if (field === 'is_primary_key' && value === true) {
      // Ensure only one primary key
      updated.forEach((col, i) => {
        col.is_primary_key = i === index;
      });
    } else {
      (updated[index] as any)[field] = value;
    }
    setColumns(updated);
  };

  const handleSaveJob = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!jobName.trim()) {
      alert("Please provide a Job Name");
      return;
    }
    if (!targetTable.trim()) {
      alert("Please provide a Target Table name");
      return;
    }
    if (columns.some(c => !c.name.trim())) {
      alert("All configured columns must have a valid name");
      return;
    }
    if (!columns.some(c => c.is_primary_key)) {
      alert("Please select at least one column as the Primary Key");
      return;
    }

    const payload = {
      name: jobName.trim(),
      folder_id: folderId,
      target_table: targetTable.trim().toUpperCase(),
      is_active: isActive,
      schedule_type: scheduleType,
      schedule_cron: scheduleType === 'cron' ? scheduleCron : undefined,
      columns_config: columns.map(c => ({
        ...c,
        name: c.name.trim()
      }))
    };

    try {
      if (editingJob) {
        await api.updateJob(editingJob.id, payload);
        setMessage({ type: 'success', text: `Job "${payload.name}" updated successfully` });
      } else {
        await api.createJob(payload);
        setMessage({ type: 'success', text: `Job "${payload.name}" created and Snowflake table "${payload.target_table}" prepared with audit columns.` });
      }
      setShowModal(false);
      await loadData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to save job' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Alert Banner */}
      {message && (
        <div
          className={`p-4 rounded-lg flex items-center justify-between text-sm ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-400'
          }`}
        >
          <div className="flex items-center space-x-2">
            {message.type === 'success' ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
            <span>{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="text-gray-400 hover:text-white ml-4 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Top Header Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            Ingestion Jobs &amp; Scheduling
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure automated file discovery, dynamic column schemas, primary keys, and Snowflake warehouse table upserts.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            title="Refresh jobs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Ingestion Job
          </button>
        </div>
      </div>

      {/* Jobs Grid / Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {(jobs || []).map((job) => {
          const folder = (folders || []).find(f => f.id === job.folder_id);
          const isRunning = runningJobId === job.id;
          const colsList = Array.isArray(job.columns_config) ? job.columns_config : [];
          const pkCol = colsList.find(c => c.is_primary_key)?.name || 'None';

          return (
            <div
              key={job.id}
              className={`bg-slate-900 border rounded-xl p-5 transition-all shadow-sm flex flex-col justify-between ${
                job.is_active ? 'border-slate-800 hover:border-slate-700' : 'border-slate-800/60 opacity-75'
              }`}
            >
              <div>
                {/* Header Line */}
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-white">{job.name}</h3>
                      <button
                        onClick={() => handleToggleActive(job)}
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full transition-colors ${
                          job.is_active
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {job.is_active ? 'Active' : 'Paused'}
                      </button>
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <FolderIcon className="w-3.5 h-3.5 text-indigo-400" />
                        Folder: <strong className="text-slate-200">{folder?.name || 'Unassigned'}</strong>
                      </span>
                      <span className="flex items-center gap-1">
                        <TableIcon className="w-3.5 h-3.5 text-emerald-400" />
                        Table: <code className="text-emerald-300 font-mono">{job.target_table}</code>
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => openEditModal(job)}
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
                      title="Edit job & columns"
                    >
                      <Settings2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteJob(job)}
                      className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                      title="Delete job"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Primary Key & Schema Columns Badges */}
                <div className="mt-4 pt-3 border-t border-slate-800">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                    <span className="flex items-center gap-1 font-medium">
                      <Key className="w-3.5 h-3.5 text-amber-400" />
                      Primary Key: <strong className="text-white font-mono">{pkCol}</strong>
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {colsList.length} Business Columns
                    </span>
                  </div>

                  {/* Column pills */}
                  <div className="flex flex-wrap gap-1.5">
                    {colsList.map((col, idx) => (
                      <span
                        key={idx}
                        className={`text-[10px] px-2 py-0.5 rounded font-mono border ${
                          col.is_primary_key
                            ? 'bg-amber-500/10 text-amber-300 border-amber-500/30 font-semibold'
                            : 'bg-slate-800/80 text-slate-300 border-slate-700/60'
                        }`}
                      >
                        {col.name} <span className="text-slate-500 text-[9px]">({col.type})</span>
                      </span>
                    ))}
                    <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 italic">
                      + CREATED_DATE
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 italic">
                      + MODIFIED_DATE
                    </span>
                  </div>
                </div>

                {/* Schedule Info */}
                <div className="mt-4 flex items-center justify-between text-xs text-slate-400 bg-slate-800/40 p-2.5 rounded-lg border border-slate-800">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                    Schedule: <strong className="text-slate-200 capitalize">{job.schedule_type}</strong>
                    {job.schedule_type === 'cron' && <code className="text-[10px] bg-slate-800 px-1 rounded font-mono">{job.schedule_cron}</code>}
                  </span>
                  {job.last_run_at && (
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Last: {new Date(job.last_run_at).toLocaleTimeString()} ({job.last_run_status})
                    </span>
                  )}
                </div>
              </div>

              {/* Bottom Trigger Button */}
              <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  Auto-discovers CSV files in folder &bull; MERGE upsert
                </span>
                <button
                  onClick={() => handleRunJob(job)}
                  disabled={isRunning || !job.is_active}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
                >
                  <Play className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
                  {isRunning ? 'Running Job...' : 'Run Now'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Create / Edit Job Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-indigo-400" />
              {editingJob ? `Edit Ingestion Job: ${editingJob.name}` : 'Create Ingestion Job'}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Connect a source folder to a Snowflake table and define the expected CSV column schema.
            </p>

            <form onSubmit={handleSaveJob} className="mt-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Job Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., DC_Employee"
                    value={jobName}
                    onChange={(e) => setJobName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Target Snowflake Table *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., EMPLOYEE"
                    value={targetTable}
                    onChange={(e) => setTargetTable(e.target.value.toUpperCase())}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono uppercase"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Source Folder *</label>
                  <select
                    value={folderId}
                    onChange={(e) => setFolderId(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {folders.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} ({f.description || 'Folder'})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Schedule</label>
                  <select
                    value={scheduleType}
                    onChange={(e) => setScheduleType(e.target.value as any)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="manual">Manual Execution Only</option>
                    <option value="hourly">Hourly (Every 60 minutes)</option>
                    <option value="daily">Daily (At 00:00 UTC)</option>
                    <option value="cron">Custom Cron Schedule</option>
                  </select>
                </div>
              </div>

              {scheduleType === 'cron' && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Cron Expression *</label>
                  <input
                    type="text"
                    placeholder="e.g., 0 */2 * * * (Every 2 hours)"
                    value={scheduleCron}
                    onChange={(e) => setScheduleCron(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {/* Dynamic Column Configuration */}
              <div className="pt-3 border-t border-slate-800">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <label className="text-xs font-semibold text-white flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      Dynamic Column Configuration
                    </label>
                    <p className="text-[11px] text-slate-400">
                      The uploaded CSV must exactly match these column names and types. Designate one Primary Key for MERGE upserting.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleAddColumn}
                    className="flex items-center gap-1 px-2.5 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-300 text-xs font-medium rounded transition-colors"
                  >
                    <Plus className="w-3 h-3" />
                    Add Column
                  </button>
                </div>

                <div className="space-y-2 mt-3 max-h-56 overflow-y-auto pr-1">
                  {columns.map((col, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 bg-slate-800/60 p-2 rounded-lg border border-slate-700/60"
                    >
                      <input
                        type="text"
                        required
                        placeholder="Column Name"
                        value={col.name}
                        onChange={(e) => handleColumnChange(idx, 'name', e.target.value)}
                        className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                      />

                      <select
                        value={col.type}
                        onChange={(e) => handleColumnChange(idx, 'type', e.target.value)}
                        className="bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="String">String</option>
                        <option value="Integer">Integer</option>
                        <option value="Float">Float</option>
                        <option value="Date">Date</option>
                        <option value="Boolean">Boolean</option>
                      </select>

                      <label className="flex items-center gap-1 text-[11px] text-amber-300 cursor-pointer px-1.5 py-1 rounded bg-amber-500/10 border border-amber-500/20">
                        <input
                          type="radio"
                          name="primary_key_radio"
                          checked={col.is_primary_key}
                          onChange={() => handleColumnChange(idx, 'is_primary_key', true)}
                          className="accent-amber-500"
                        />
                        <span>PK</span>
                      </label>

                      <button
                        type="button"
                        onClick={() => handleRemoveColumn(idx)}
                        className="p-1 text-slate-400 hover:text-rose-400 rounded transition-colors"
                        title="Remove column"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Audit Columns Notice */}
                <div className="mt-3 p-3 bg-indigo-950/30 border border-indigo-500/20 rounded-lg text-[11px] text-indigo-300 flex items-start gap-2">
                  <Database className="w-4 h-4 flex-shrink-0 text-indigo-400 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">Automatic Audit Columns:</span> The platform automatically appends{' '}
                    <code className="text-white font-mono font-semibold">CREATED_DATE</code> and{' '}
                    <code className="text-white font-mono font-semibold">MODIFIED_DATE</code> to the Snowflake table.
                    These timestamps are managed exclusively by the backend ingestion engine.
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-colors"
                >
                  {editingJob ? 'Save Job Changes' : 'Create Job & Prepare Table'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
