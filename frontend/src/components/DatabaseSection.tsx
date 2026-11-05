'use client';

import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Table as TableIcon, 
  Search, 
  ArrowUpDown, 
  RefreshCw, 
  Key, 
  Clock, 
  SlidersHorizontal,
  Cloud,
  HardDrive,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Calendar
} from 'lucide-react';
import { TableColumnSchema, TableDataResponse, SnowflakeStatus } from '../types';
import { api } from '../lib/api';

interface DatabaseSectionProps {
  onOpenSnowflakeSettings: () => void;
}

export default function DatabaseSection({ onOpenSnowflakeSettings }: DatabaseSectionProps) {
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [columnsSchema, setColumnsSchema] = useState<TableColumnSchema[]>([]);
  const [tableData, setTableData] = useState<TableDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [status, setStatus] = useState<SnowflakeStatus | null>(null);
  const pageSize = 10;

  useEffect(() => {
    loadStatus();
    loadTables();
  }, []);

  useEffect(() => {
    if (selectedTable) {
      loadTableSchema(selectedTable);
      loadTableRecords(selectedTable, 1, searchQuery, sortBy, sortOrder);
    }
  }, [selectedTable]);

  const loadStatus = async () => {
    try {
      const st = await api.getDatabaseStatus();
      setStatus(st);
    } catch {
      // ignore
    }
  };

  const loadTables = async () => {
    try {
      const res = await api.getTables();
      const rawList = Array.isArray(res) 
        ? res 
        : (res && Array.isArray((res as any).tables) ? (res as any).tables : []);
      const tableList: string[] = rawList.map((t: any) => (typeof t === 'string' ? t : t?.name || '')).filter(Boolean);
      
      setTables(tableList);
      if (tableList.length > 0 && (!selectedTable || !tableList.includes(selectedTable))) {
        setSelectedTable(tableList[0]);
      }
    } catch {
      // ignore
    }
  };

  const loadTableSchema = async (tableName: string) => {
    try {
      const res = await api.getTableSchema(tableName);
      const cols: TableColumnSchema[] = Array.isArray(res)
        ? res
        : (res && Array.isArray((res as any).columns) ? (res as any).columns : []);
      setColumnsSchema(cols);
    } catch {
      // ignore
    }
  };

  const loadTableRecords = async (
    tableName: string,
    page: number,
    search: string,
    sortField: string,
    order: 'asc' | 'desc'
  ) => {
    setLoading(true);
    try {
      const res = await api.getTableData(tableName, {
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        sort_by: sortField || undefined,
        sort_order: order,
      });
      setTableData(res);
      setCurrentPage(page);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedTable) {
      loadTableRecords(selectedTable, 1, searchQuery, sortBy, sortOrder);
    }
  };

  const handleSort = (columnName: string) => {
    const nextOrder = sortBy === columnName && sortOrder === 'asc' ? 'desc' : 'asc';
    setSortBy(columnName);
    setSortOrder(nextOrder);
    if (selectedTable) {
      loadTableRecords(selectedTable, 1, searchQuery, columnName, nextOrder);
    }
  };

  const handleRefresh = () => {
    if (selectedTable) {
      loadTableSchema(selectedTable);
      loadTableRecords(selectedTable, currentPage, searchQuery, sortBy, sortOrder);
      loadStatus();
    }
  };

  const totalPages = tableData ? Math.ceil(tableData.total_records / pageSize) : 1;

  return (
    <div className="space-y-6">
      {/* Top Banner: Status & Engine info */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-semibold text-white">Snowflake Warehouse Tables</h2>
            {status?.is_cloud ? (
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <Cloud className="w-3.5 h-3.5" />
                Snowflake Cloud Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/30">
                <HardDrive className="w-3.5 h-3.5" />
                Local Warehouse Mode (Engine Active)
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Query ingested tables, audit timestamps (<code className="text-indigo-300">CREATED_DATE</code>, <code className="text-indigo-300">MODIFIED_DATE</code>), and inspect MERGE upsert outcomes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            title="Refresh database view"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onOpenSnowflakeSettings}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-colors shadow-sm"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-400" />
            Snowflake Settings
          </button>
        </div>
      </div>

      {/* Table Selector Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-400 mr-2">Select Table:</span>
        {tables.map((t) => {
          const isSelected = selectedTable === t;
          return (
            <button
              key={t}
              onClick={() => setSelectedTable(t)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium border transition-all ${
                isSelected
                  ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-sm'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>{t}</span>
            </button>
          );
        })}
      </div>

      {/* Schema Columns Badges */}
      {selectedTable && columnsSchema.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Table Schema Structure: <span className="font-mono text-white">{selectedTable}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {columnsSchema.map((col) => {
              const isAudit = col.is_audit_column;
              const isPK = col.is_primary_key;

              return (
                <div
                  key={col.name}
                  className={`text-xs px-2.5 py-1.5 rounded-lg border font-mono flex items-center gap-2 ${
                    isPK
                      ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                      : isAudit
                      ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                      : 'bg-slate-800 border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-1">
                    {isPK && <Key className="w-3 h-3 text-amber-400" />}
                    {isAudit && <Clock className="w-3 h-3 text-indigo-400" />}
                    <span className="font-semibold">{col.name}</span>
                  </div>
                  <span className="text-[10px] text-slate-400">({col.type})</span>
                  {isPK && <span className="text-[9px] bg-amber-400/20 text-amber-300 px-1 rounded uppercase">Primary Key</span>}
                  {isAudit && <span className="text-[9px] bg-indigo-400/20 text-indigo-300 px-1 rounded uppercase">Audit</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Table Data Viewer */}
      {selectedTable && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          {/* Controls: Search & Total Count */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <form onSubmit={handleSearchSubmit} className="relative max-w-sm w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder={`Search records in ${selectedTable}...`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </form>

            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span>
                Total Ingested: <strong className="text-white font-mono">{tableData?.total_records || 0}</strong> records
              </span>
              <span className="text-slate-600">&bull;</span>
              <span>
                Engine: <strong className="text-indigo-300 font-mono">{tableData?.engine_mode || status?.mode_label}</strong>
              </span>
            </div>
          </div>

          {/* Records Table */}
          <div className="mt-4 overflow-x-auto">
            {tableData?.records && tableData.records.length > 0 ? (
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-800/60 text-slate-300">
                  <tr>
                    {(tableData.columns || []).map((col) => {
                      const colName = typeof col === 'string' ? col : ((col as any)?.name || '');
                      const isAudit = colName === 'CREATED_DATE' || colName === 'MODIFIED_DATE';
                      const isPK = (columnsSchema || []).find(c => c.name === colName)?.is_primary_key;

                      return (
                        <th
                          key={colName}
                          onClick={() => handleSort(colName)}
                          className={`py-2.5 px-3 cursor-pointer hover:bg-slate-800 transition-colors select-none ${
                            isAudit ? 'text-indigo-300' : isPK ? 'text-amber-300' : 'text-slate-300'
                          }`}
                        >
                          <div className="flex items-center gap-1.5">
                            <span>{colName}</span>
                            <ArrowUpDown className="w-3 h-3 text-slate-500" />
                          </div>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {tableData.records.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                      {(tableData.columns || []).map((col) => {
                        const colName = typeof col === 'string' ? col : ((col as any)?.name || '');
                        const val = row[colName];
                        const isAudit = colName === 'CREATED_DATE' || colName === 'MODIFIED_DATE';
                        const isPK = (columnsSchema || []).find(c => c.name === colName)?.is_primary_key;

                        return (
                          <td
                            key={colName}
                            className={`py-2.5 px-3 ${
                              isPK
                                ? 'font-bold text-amber-300'
                                : isAudit
                                ? 'text-indigo-300 text-[11px]'
                                : 'text-slate-200'
                            }`}
                          >
                            {val !== null && val !== undefined ? String(val) : <span className="text-slate-600 italic">null</span>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="py-12 flex flex-col items-center justify-center text-center">
                <TableIcon className="w-10 h-10 text-slate-600 mb-2" />
                <p className="text-xs text-slate-400 font-medium">No records found in table "{selectedTable}".</p>
                <p className="text-[11px] text-slate-500 mt-1">Upload a CSV in "File Upload" and trigger the job to ingest records.</p>
              </div>
            )}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
              <div>
                Page <strong className="text-white">{currentPage}</strong> of <strong className="text-white">{totalPages}</strong>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => loadTableRecords(selectedTable, Math.max(1, currentPage - 1), searchQuery, sortBy, sortOrder)}
                  disabled={currentPage <= 1 || loading}
                  className="p-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => loadTableRecords(selectedTable, Math.min(totalPages, currentPage + 1), searchQuery, sortBy, sortOrder)}
                  disabled={currentPage >= totalPages || loading}
                  className="p-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
