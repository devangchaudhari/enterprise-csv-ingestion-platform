'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  FolderPlus, 
  UploadCloud, 
  FileText, 
  Trash2, 
  RefreshCw, 
  Folder as FolderIcon, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Play,
  FileCheck
} from 'lucide-react';
import { Folder, UploadedFile, IngestionJob } from '../types';
import { api } from '../lib/api';

interface FileUploadSectionProps {
  onRunJobSuccess?: () => void;
}

export default function FileUploadSection({ onRunJobSuccess }: FileUploadSectionProps) {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [newFolderDesc, setNewFolderDesc] = useState('');
  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [runningJobId, setRunningJobId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadFolders();
    loadJobs();
  }, []);

  useEffect(() => {
    if (selectedFolder) {
      loadFiles(selectedFolder.id);
    }
  }, [selectedFolder]);

  const loadFolders = async () => {
    try {
      const data = await api.getFolders();
      setFolders(data);
      if (data.length > 0 && !selectedFolder) {
        setSelectedFolder(data[0]);
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to load folders' });
    }
  };

  const loadJobs = async () => {
    try {
      const jobList = await api.getJobs();
      setJobs(jobList);
    } catch (err) {
      // ignore
    }
  };

  const loadFiles = async (folderId: string) => {
    setLoading(true);
    try {
      const data = await api.getFiles(folderId);
      setFiles(data);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to load files' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    try {
      const newFolder = await api.createFolder({
        name: newFolderName.trim(),
        description: newFolderDesc.trim() || undefined,
      });
      setFolders([...folders, newFolder]);
      setSelectedFolder(newFolder);
      setNewFolderName('');
      setNewFolderDesc('');
      setShowNewFolderModal(false);
      setMessage({ type: 'success', text: `Folder "${newFolder.name}" created successfully` });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to create folder' });
    }
  };

  const handleDeleteFolder = async (folder: Folder) => {
    if (!confirm(`Are you sure you want to delete folder "${folder.name}"?`)) return;
    try {
      await api.deleteFolder(folder.id);
      const remaining = folders.filter((f) => f.id !== folder.id);
      setFolders(remaining);
      setSelectedFolder(remaining.length > 0 ? remaining[0] : null);
      setMessage({ type: 'success', text: `Folder "${folder.name}" deleted` });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to delete folder' });
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedFolder) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setMessage({ type: 'error', text: 'Please select a valid CSV file (.csv)' });
      return;
    }

    setUploading(true);
    setMessage(null);
    try {
      await api.uploadFile(selectedFolder.id, file);
      setMessage({ type: 'success', text: `File "${file.name}" uploaded successfully into "${selectedFolder.name}" folder` });
      await loadFiles(selectedFolder.id);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'File upload failed' });
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteFile = async (file: UploadedFile) => {
    if (!confirm(`Delete file "${file.filename}" before processing?`)) return;
    try {
      await api.deleteFile(file.id);
      setFiles(files.filter((f) => f.id !== file.id));
      setMessage({ type: 'success', text: `File "${file.filename}" deleted` });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to delete file' });
    }
  };

  const handleRunFolderJob = async () => {
    if (!selectedFolder) return;
    const associatedJob = jobs.find((j) => j.folder_id === selectedFolder.id);
    if (!associatedJob) {
      setMessage({
        type: 'error',
        text: `No active ingestion job configured for folder "${selectedFolder.name}". Please create one in the Jobs section.`,
      });
      return;
    }

    setRunningJobId(associatedJob.id);
    setMessage(null);
    try {
      const resp = await api.runJob(associatedJob.id);
      const resCount = resp.results.length;
      setMessage({
        type: 'success',
        text: `Executed job "${associatedJob.name}". Processed ${resCount} file(s). View details in Jobs & Database sections.`,
      });
      await loadFiles(selectedFolder.id);
      if (onRunJobSuccess) onRunJobSuccess();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Job run failed' });
      await loadFiles(selectedFolder.id);
    } finally {
      setRunningJobId(null);
    }
  };

  const associatedJob = selectedFolder ? jobs.find((j) => j.folder_id === selectedFolder.id) : null;
  const pendingFilesCount = files.filter((f) => f.status === 'pending').length;

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

      {/* Top Section: Folder Selector and Creator */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <FolderIcon className="w-5 h-5 text-indigo-400" />
              Source Ingestion Folders
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Select or create target directories for different business datasets (e.g., Employee, Customer, Product).
            </p>
          </div>
          <button
            onClick={() => setShowNewFolderModal(true)}
            className="flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors shadow-sm self-start sm:self-auto"
          >
            <FolderPlus className="w-4 h-4" />
            Create Folder
          </button>
        </div>

        {/* Folder Pills */}
        <div className="flex flex-wrap gap-2.5 mt-4">
          {folders.map((folder) => {
            const isSelected = selectedFolder?.id === folder.id;
            return (
              <button
                key={folder.id}
                onClick={() => setSelectedFolder(folder)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-medium border transition-all ${
                  isSelected
                    ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-sm'
                    : 'bg-slate-800/60 border-slate-700/60 text-slate-300 hover:bg-slate-800 hover:border-slate-600'
                }`}
              >
                <FolderIcon className={`w-4 h-4 ${isSelected ? 'text-indigo-400' : 'text-slate-400'}`} />
                <span>{folder.name}</span>
                {folder.name === 'Employee' && (
                  <span className="text-[10px] bg-indigo-500/30 text-indigo-300 px-1.5 py-0.5 rounded">Primary</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Folder Detail & Upload Area */}
      {selectedFolder && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Upload Card */}
          <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Active Folder</span>
                <button
                  onClick={() => handleDeleteFolder(selectedFolder)}
                  className="text-slate-500 hover:text-rose-400 text-xs transition-colors"
                  title="Delete this folder"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <h3 className="text-xl font-bold text-white mt-1">{selectedFolder.name}</h3>
              <p className="text-xs text-slate-400 mt-1">
                {selectedFolder.description || 'Dedicated CSV drop folder for enterprise data ingestion.'}
              </p>

              {/* Associated Job Info */}
              <div className="mt-4 p-3 bg-slate-800/60 rounded-lg border border-slate-700/50">
                <div className="text-[11px] text-slate-400 font-medium">Associated Ingestion Job</div>
                {associatedJob ? (
                  <div className="mt-1 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-white">{associatedJob.name}</div>
                      <div className="text-[10px] text-slate-400">Target Table: <span className="text-indigo-300 font-mono">{associatedJob.target_table}</span></div>
                    </div>
                    <button
                      onClick={handleRunFolderJob}
                      disabled={runningJobId === associatedJob.id || pendingFilesCount === 0}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-[11px] font-medium rounded transition-colors"
                      title={pendingFilesCount === 0 ? "No pending files waiting" : "Run job now"}
                    >
                      <Play className="w-3 h-3" />
                      {runningJobId === associatedJob.id ? 'Running...' : 'Run Job'}
                    </button>
                  </div>
                ) : (
                  <div className="text-xs text-amber-400 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    No job linked yet. Create job in "Jobs" tab.
                  </div>
                )}
              </div>
            </div>

            {/* Drag & Drop Upload Trigger */}
            <div className="mt-6">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
                id="csv-file-upload"
              />
              <label
                htmlFor="csv-file-upload"
                className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                  uploading
                    ? 'border-indigo-500 bg-indigo-500/10 cursor-not-allowed'
                    : 'border-slate-700 hover:border-indigo-500 bg-slate-800/40 hover:bg-slate-800/80'
                }`}
              >
                <UploadCloud className={`w-10 h-10 mb-2 ${uploading ? 'text-indigo-400 animate-pulse' : 'text-slate-400'}`} />
                <span className="text-xs font-medium text-white">
                  {uploading ? 'Uploading CSV to storage...' : 'Click or drop CSV here'}
                </span>
                <span className="text-[11px] text-slate-400 mt-1">
                  Uploads directly to <code className="text-indigo-300">./storage/uploads/{selectedFolder.name}/</code>
                </span>
              </label>
            </div>
          </div>

          {/* Files List Table */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  Files in "{selectedFolder.name}" Folder
                </h3>
                <span className="text-xs text-slate-400">
                  {pendingFilesCount} waiting to be ingested &bull; {files.length} total recorded
                </span>
              </div>
              <button
                onClick={() => selectedFolder && loadFiles(selectedFolder.id)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
                title="Refresh file list"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {files.length === 0 ? (
              <div className="py-12 flex flex-col items-center justify-center text-center">
                <FileCheck className="w-10 h-10 text-slate-600 mb-2" />
                <p className="text-xs text-slate-400 font-medium">No CSV files in this folder.</p>
                <p className="text-[11px] text-slate-500 mt-1">Upload a CSV to stage files for automatic ingestion.</p>
              </div>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800/50 text-slate-400 font-medium">
                    <tr>
                      <th className="py-2.5 px-3">File Name</th>
                      <th className="py-2.5 px-3">Size</th>
                      <th className="py-2.5 px-3">Uploaded</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {files.map((file) => {
                      const isPending = file.status === 'pending';
                      const isProcessed = file.status === 'processed';
                      const isFailed = file.status === 'failed';

                      return (
                        <tr key={file.id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-3">
                            <div className="font-medium text-white flex items-center gap-2">
                              <FileText className="w-3.5 h-3.5 text-slate-400" />
                              <span>{file.filename}</span>
                            </div>
                            {file.error_message && (
                              <div className="text-[10px] text-rose-400 mt-1 bg-rose-500/10 p-1.5 rounded border border-rose-500/20 max-w-md">
                                <span className="font-semibold">Error:</span> {file.error_message}
                              </div>
                            )}
                          </td>
                          <td className="py-3 px-3 text-slate-400 font-mono text-[11px]">
                            {(file.file_size_bytes / 1024).toFixed(1)} KB
                          </td>
                          <td className="py-3 px-3 text-slate-400">
                            {(() => {
                              const d = file.uploaded_at || file.created_at;
                              if (!d) return 'Recent';
                              const parsed = new Date(d);
                              return isNaN(parsed.getTime()) ? 'Recent' : parsed.toLocaleString();
                            })()}
                          </td>
                          <td className="py-3 px-3">
                            {isPending && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                <Clock className="w-2.5 h-2.5" />
                                Waiting Ingestion
                              </span>
                            )}
                            {isProcessed && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                <CheckCircle2 className="w-2.5 h-2.5" />
                                Processed
                              </span>
                            )}
                            {isFailed && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                                <AlertCircle className="w-2.5 h-2.5" />
                                Failed (Retained)
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-right">
                            {/* Can delete before processed or if failed */}
                            {isPending && (
                              <button
                                onClick={() => handleDeleteFile(file)}
                                className="p-1 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                                title="Delete file before processing"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                            {isFailed && (
                              <button
                                onClick={() => handleDeleteFile(file)}
                                className="p-1 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                                title="Remove failed file"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                            {isProcessed && (
                              <span className="text-[10px] text-slate-500 italic">Deleted from disk</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New Folder Modal */}
      {showNewFolderModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <FolderPlus className="w-5 h-5 text-indigo-400" />
              Create Ingestion Folder
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Folders organize incoming CSV files by dataset domain (e.g. Employee, Customer, Products).
            </p>

            <form onSubmit={handleCreateFolder} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Folder Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Customer, Product, Inventory"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Optional brief description of the dataset"
                  value={newFolderDesc}
                  onChange={(e) => setNewFolderDesc(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewFolderModal(false)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-colors"
                >
                  Create Folder
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
