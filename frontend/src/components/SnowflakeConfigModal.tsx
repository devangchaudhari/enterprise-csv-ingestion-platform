'use client';

import React, { useState, useEffect } from 'react';
import { 
  Cloud, 
  HardDrive, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  SlidersHorizontal,
  KeyRound,
  Database
} from 'lucide-react';
import { SnowflakeConfig } from '../types';
import { api } from '../lib/api';

interface SnowflakeConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigSaved?: () => void;
}

export default function SnowflakeConfigModal({ isOpen, onClose, onConfigSaved }: SnowflakeConfigModalProps) {
  const [account, setAccount] = useState('');
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [warehouse, setWarehouse] = useState('');
  const [database, setDatabase] = useState('');
  const [schemaName, setSchemaName] = useState('PUBLIC');
  const [isActive, setIsActive] = useState(false);

  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  const loadConfig = async () => {
    try {
      const cfg = await api.getSnowflakeConfig();
      if (cfg) {
        setAccount(cfg.account || '');
        setUser(cfg.user || '');
        setPassword(cfg.password || '');
        setWarehouse(cfg.warehouse || '');
        setDatabase(cfg.database || '');
        setSchemaName(cfg.schema_name || 'PUBLIC');
        setIsActive(cfg.is_active || false);
      }
    } catch {
      // ignore
    }
  };

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    setTesting(true);
    setFeedback(null);
    try {
      const res = await api.testSnowflakeConnection({
        account: account.trim(),
        user: user.trim(),
        password: password.trim(),
        warehouse: warehouse.trim(),
        database: database.trim(),
        schema_name: schemaName.trim()
      });
      if (res.success) {
        setFeedback({ type: 'success', text: `Connection successful! Snowflake version: ${res.version || 'Active'}` });
      } else {
        setFeedback({ type: 'error', text: res.message || 'Connection test failed.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Snowflake connection failed. Check account credentials.' });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      await api.saveSnowflakeConfig({
        account: account.trim(),
        user: user.trim(),
        password: password.trim(),
        warehouse: warehouse.trim(),
        database: database.trim(),
        schema_name: schemaName.trim(),
        is_active: isActive
      });
      setFeedback({ type: 'success', text: 'Snowflake configuration saved successfully!' });
      if (onConfigSaved) onConfigSaved();
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Failed to save configuration.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-5 h-5 text-indigo-400" />
          <h3 className="text-base font-semibold text-white">Snowflake Warehouse Settings</h3>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Configure live Snowflake credentials or run effortlessly in Local Warehouse Mode (PostgreSQL / SQLite Engine).
        </p>

        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`mt-4 p-3 rounded-lg flex items-center space-x-2 text-xs ${
              feedback.type === 'success'
                ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
                : 'bg-rose-500/10 border border-rose-500/30 text-rose-400'
            }`}
          >
            {feedback.type === 'success' ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
            <span>{feedback.text}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="mt-4 space-y-3.5">
          {/* Active Mode Toggle */}
          <div className="p-3 bg-slate-800/60 rounded-lg border border-slate-700/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cloud className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
              <div>
                <div className="text-xs font-semibold text-white">Snowflake Cloud Ingestion</div>
                <div className="text-[10px] text-slate-400">
                  {isActive ? 'Dual ingest enabled to Snowflake Cloud' : 'Disabled — Running strictly in Local Warehouse Mode'}
                </div>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Account Identifier</label>
              <input
                type="text"
                placeholder="xy12345.us-east-1"
                value={account}
                onChange={(e) => setAccount(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Username</label>
              <input
                type="text"
                placeholder="DW_INGEST_USER"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Password</label>
              <input
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Warehouse</label>
              <input
                type="text"
                placeholder="COMPUTE_WH"
                value={warehouse}
                onChange={(e) => setWarehouse(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Database</label>
              <input
                type="text"
                placeholder="RETAIL_DW"
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">Schema</label>
              <input
                type="text"
                placeholder="PUBLIC"
                value={schemaName}
                onChange={(e) => setSchemaName(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>

          <div className="p-3 bg-slate-800/40 rounded-lg border border-slate-800 text-[11px] text-slate-400">
            <span className="font-semibold text-slate-300">Local Warehouse Alternative:</span> All operations execute in the built-in local warehouse engine with the exact same SQL MERGE upsert syntax, schema creation, and automatic audit columns.
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing || !account || !user}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-xs font-semibold rounded transition-colors border border-slate-700"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded transition-colors"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
