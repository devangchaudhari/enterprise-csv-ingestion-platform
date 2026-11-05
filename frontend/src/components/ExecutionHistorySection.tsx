'use client';

import React, { useState, useEffect } from 'react';
import { 
  History, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  RefreshCw, 
  FileText, 
  Calendar,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { JobExecution } from '../types';
import { api } from '../lib/api';

export default function ExecutionHistorySection() {
  const [history, setHistory] = useState<JobExecution[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await api.getJobHistory();
      setHistory(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            Job Execution &amp; Audit Logs
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Audit trail of all manual and scheduled ingestion jobs, records inserted/updated, and validation errors.
          </p>
        </div>
        <button
          onClick={loadHistory}
          className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors self-start sm:self-auto"
          title="Refresh history"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* History Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        {history.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center text-center">
            <Clock className="w-10 h-10 text-slate-600 mb-2" />
            <p className="text-xs text-slate-400 font-medium">No job executions recorded yet.</p>
            <p className="text-[11px] text-slate-500 mt-1">Execute a job from the "Jobs" or "File Upload" section to record history.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/60 text-slate-400 font-medium">
                <tr>
                  <th className="py-2.5 px-3">Job Name</th>
                  <th className="py-2.5 px-3">Execution Time</th>
                  <th className="py-2.5 px-3">Trigger</th>
                  <th className="py-2.5 px-3">File Processed</th>
                  <th className="py-2.5 px-3">Processed</th>
                  <th className="py-2.5 px-3">Inserted</th>
                  <th className="py-2.5 px-3">Updated</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Details / Errors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {history.map((item) => {
                  const isSuccess = item.execution_status === 'Success';
                  const isFailed = item.execution_status === 'Failed';

                  return (
                    <tr key={item.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-3 font-semibold text-white">
                        {item.job_name}
                      </td>
                      <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                        {(() => {
                          if (!item.execution_time) return 'N/A';
                          const parsed = new Date(item.execution_time);
                          return isNaN(parsed.getTime()) ? 'N/A' : parsed.toLocaleString();
                        })()}
                      </td>
                      <td className="py-3 px-3">
                        <span className="capitalize px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                          {item.execution_type}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-slate-300">
                        {item.file_name ? (
                          <span className="flex items-center gap-1">
                            <FileText className="w-3 h-3 text-slate-400" />
                            {item.file_name}
                          </span>
                        ) : (
                          <span className="text-slate-600 italic">None</span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono font-semibold text-white">
                        {item.records_processed}
                      </td>
                      <td className="py-3 px-3 font-mono text-emerald-400">
                        +{item.records_inserted}
                      </td>
                      <td className="py-3 px-3 font-mono text-indigo-400">
                        {item.records_updated}
                      </td>
                      <td className="py-3 px-3">
                        {isSuccess && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            <CheckCircle2 className="w-2.5 h-2.5" />
                            Success
                          </span>
                        )}
                        {isFailed && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                            <AlertCircle className="w-2.5 h-2.5" />
                            Failed
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 max-w-xs">
                        {item.error_details ? (
                          <div className="text-[11px] text-rose-400 bg-rose-500/10 p-1.5 rounded border border-rose-500/20 truncate" title={item.error_details}>
                            {item.error_details}
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-500">Normal execution</span>
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
  );
}
