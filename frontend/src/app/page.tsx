'use client';

import React, { useState, useEffect } from 'react';
import { 
  UploadCloud, 
  Layers, 
  Database, 
  History, 
  Cloud, 
  HardDrive, 
  SlidersHorizontal,
  CheckCircle2,
  Folder as FolderIcon,
  Play,
  FileText
} from 'lucide-react';
import FileUploadSection from '../components/FileUploadSection';
import JobsSection from '../components/JobsSection';
import DatabaseSection from '../components/DatabaseSection';
import ExecutionHistorySection from '../components/ExecutionHistorySection';
import SnowflakeConfigModal from '../components/SnowflakeConfigModal';
import { SnowflakeStatus } from '../types';
import { api } from '../lib/api';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'upload' | 'jobs' | 'database' | 'history'>('upload');
  const [status, setStatus] = useState<SnowflakeStatus | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    loadDatabaseStatus();
  }, [refreshTrigger]);

  const loadDatabaseStatus = async () => {
    try {
      const st = await api.getDatabaseStatus();
      setStatus(st);
    } catch {
      // ignore
    }
  };

  const handleJobOrUploadSuccess = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased selection:bg-indigo-500 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Title & Branding */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <Database className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-sm sm:text-base font-bold text-white tracking-tight flex items-center gap-2">
                  Enterprise CSV Data Ingestion Platform
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                    v2.0
                  </span>
                </h1>
                <p className="text-[11px] text-slate-400 hidden sm:block">
                  Automated CSV Folder Ingestion &bull; Dynamic Schema Validation &bull; Snowflake Warehouse MERGE Upserts
                </p>
              </div>
            </div>

            {/* Warehouse Status & Settings Button */}
            <div className="flex items-center gap-3">
              {status?.is_cloud || status?.is_cloud_connected ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <Cloud className="w-3.5 h-3.5" />
                  <span className="hidden md:inline">Snowflake Cloud Connected</span>
                  <span className="md:hidden">Snowflake</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/30">
                  <HardDrive className="w-3.5 h-3.5" />
                  <span className="hidden md:inline">Local Warehouse Mode</span>
                  <span className="md:hidden">Local DW</span>
                </div>
              )}

              <button
                onClick={() => setShowConfigModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
                title="Configure Snowflake credentials"
              >
                <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-400" />
                <span className="hidden sm:inline">Settings</span>
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-1 sm:space-x-4 border-t border-slate-800/60 overflow-x-auto py-2">
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                activeTab === 'upload'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <UploadCloud className="w-4 h-4" />
              <span>1. File Upload</span>
            </button>

            <button
              onClick={() => setActiveTab('jobs')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                activeTab === 'jobs'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>2. Jobs &amp; Scheduling</span>
            </button>

            <button
              onClick={() => setActiveTab('database')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                activeTab === 'database'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Database className="w-4 h-4" />
              <span>3. Database (Snowflake)</span>
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                activeTab === 'history'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <History className="w-4 h-4" />
              <span>Execution History</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'upload' && <FileUploadSection onRunJobSuccess={handleJobOrUploadSuccess} />}
        {activeTab === 'jobs' && <JobsSection onJobExecuted={handleJobOrUploadSuccess} />}
        {activeTab === 'database' && (
          <DatabaseSection onOpenSnowflakeSettings={() => setShowConfigModal(true)} />
        )}
        {activeTab === 'history' && <ExecutionHistorySection />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/50 py-4 text-center text-xs text-slate-500">
        Enterprise CSV Data Ingestion &amp; Workflow Automation Platform &bull; Snowflake &amp; Local Warehouse Hybrid Engine
      </footer>

      {/* Snowflake Settings Modal */}
      <SnowflakeConfigModal
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onConfigSaved={handleJobOrUploadSuccess}
      />
    </div>
  );
}
