"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, Settings, Database, Cpu, Trash2, Upload, 
  Check, AlertCircle, FileText, Globe, Palette 
} from "lucide-react";
import { uploadFiles, fetchExternalProcess, getUploadStatus, cancelUpload, getStats, deleteDocument, clearDatabase, getConfig, updateConfig } from "@/lib/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  subjects: string[];
  initialTab?: Tab;
}

type Tab = "geral" | "dados" | "documentos" | "motor";

export default function SettingsModal({ isOpen, onClose, subjects, initialTab = "geral" }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>(initialTab);

  useEffect(() => {
    if (isOpen) setActiveTab(initialTab);
  }, [isOpen, initialTab]);
  
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        />

        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-[840px] h-[600px] bg-[#171717] border border-[#333] rounded-2xl shadow-2xl overflow-hidden flex"
        >
          <aside className="w-64 bg-[#121212] border-r border-[#333] p-4 flex flex-col gap-1">
            <div className="px-3 py-4 mb-2 text-white font-semibold flex items-center gap-2">
              <Settings size={20} className="text-[#888]" />
              Configurações
            </div>

            <TabButton active={activeTab === "geral"} onClick={() => setActiveTab("geral")} icon={<Settings size={18} />} label="Geral" />
            <TabButton active={activeTab === "dados"} onClick={() => setActiveTab("dados")} icon={<Upload size={18} />} label="Upload de Dados" />
            <TabButton active={activeTab === "documentos"} onClick={() => setActiveTab("documentos")} icon={<FileText size={18} />} label="Documentos" />
            <TabButton active={activeTab === "motor"} onClick={() => setActiveTab("motor")} icon={<Cpu size={18} />} label="Motor RAG" />
          </aside>

          <div className="flex-1 flex flex-col bg-[#171717]">
            <header className="h-14 flex items-center justify-end px-4 border-b border-[#333]/30">
              <button onClick={onClose} className="p-2 text-[#666] hover:text-white rounded-lg transition-all"><X size={20} /></button>
            </header>

            <main className="flex-1 overflow-y-auto p-8 pt-4 custom-scrollbar">
              {activeTab === "geral" && <GeralTab />}
              {activeTab === "dados" && <UploadTab />}
              {activeTab === "documentos" && <DocumentosTab />}
              {activeTab === "motor" && <MotorTab />}
            </main>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: React.ReactNode, label: string }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${active ? "bg-[#2f2f2f] text-white" : "text-[#999] hover:bg-[#1f1f1f] hover:text-white"}`}>
      <span className={active ? "text-white" : "text-[#555]"}>{icon}</span>
      {label}
    </button>
  );
}

function GeralTab() {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-medium text-white">Geral</h3>
      <div className="space-y-4">
        <SettingItem icon={<Palette size={18} />} title="Aparência" description="Interface do sistema." action={<Select value="Escuro" />} />
        <SettingItem icon={<Globe size={18} />} title="Idioma" description="Idioma das respostas." action={<Select value="Português (BR)" />} />
      </div>
    </div>
  );
}

function UploadTab() {
  const [processNumber, setProcessNumber] = useState("");
  const [fetching, setFetching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [subject, setSubject] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const [useOcr, setUseOcr] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatCNJ = (val: string) => {
    const d = val.replace(/\D/g, "").slice(0, 20);
    let f = d;
    if (d.length > 7) f = `${d.slice(0, 7)}-${d.slice(7)}`;
    if (d.length > 9) f = `${f.slice(0, 10)}.${d.slice(9)}`;
    if (d.length > 13) f = `${f.slice(0, 15)}.${d.slice(13)}`;
    if (d.length > 14) f = `${f.slice(0, 17)}.${d.slice(14)}`;
    if (d.length > 16) f = `${f.slice(0, 20)}.${d.slice(16)}`;
    return f;
  };

  const handleSync = async () => {
    if (!processNumber.trim()) return;
    setFetching(true); setError(null); setSuccess(false);
    try {
      const res = await fetchExternalProcess(processNumber);
      if (res.success) { setSuccess(true); setProcessNumber(""); }
      else throw new Error(res.message);
    } catch (e: any) { setError(e.message || "Erro na conexão judicial"); }
    finally { setFetching(false); }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true); setError(null); setSuccess(false); setProgress(0);
    try {
      const res = await uploadFiles(selectedFiles, subject, useOcr);
      if (res.success && res.task_id) {
        const interval = setInterval(async () => {
          const status = await getUploadStatus(res.task_id);
          setProgress(status.progress);
          if (status.status === "completed") {
            clearInterval(interval); setUploading(false); setSuccess(true); setSelectedFiles([]); setSubject("");
          } else if (status.status === "failed") {
            clearInterval(interval); setUploading(false); setError(status.message);
          }
        }, 1000);
      }
    } catch (e: any) { setError(e.message); setUploading(false); }
  };

  return (
    <div className="space-y-10">
      <section>
        <div className="mb-5"><h3 className="text-lg font-semibold text-white">Sincronização Judicial</h3><p className="text-xs text-[#666]">Importe andamentos via CNJ/DataJud.</p></div>
        <div className="bg-[#1a1a1a] border border-[#333] rounded-xl p-5">
          <div className="flex gap-2">
            <input type="text" value={processNumber} onChange={e => setProcessNumber(formatCNJ(e.target.value))} placeholder="0000000-00.0000.0.00.0000" disabled={fetching} className="flex-1 bg-[#121212] border border-[#222] rounded-lg px-4 py-2 text-sm text-white font-mono outline-none focus:border-blue-500/30" />
            <button onClick={handleSync} disabled={fetching || !processNumber} className="px-5 py-2 bg-[#2f2f2f] text-white rounded-lg text-xs font-bold hover:bg-[#3f3f3f] flex items-center gap-2 border border-[#444]">
              {fetching ? <div className="w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin" /> : <Globe size={14} />} Sincronizar
            </button>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-5 flex justify-between items-center">
          <div><h3 className="text-lg font-semibold text-white">Documentos Internos</h3><p className="text-xs text-[#666]">Upload de arquivos locais.</p></div>
          {uploading && <div className="text-[10px] text-blue-400 font-bold animate-pulse">{progress}% INDEXANDO</div>}
        </div>
        <div className="bg-[#1a1a1a] border border-[#333] rounded-xl p-5 space-y-4 relative overflow-hidden">
          {uploading && <div className="absolute top-0 left-0 h-[2px] bg-blue-500/30 transition-all duration-300" style={{ width: `${progress}%` }} />}
          <div className="grid grid-cols-2 gap-3">
            <input type="text" value={subject} onChange={e => setSubject(e.target.value)} placeholder="Assunto..." className="bg-[#121212] border border-[#222] rounded-lg px-3 py-2 text-sm text-white outline-none" />
            <button onClick={() => setUseOcr(!useOcr)} className={`px-3 py-2 rounded-lg border text-xs font-medium ${useOcr ? "bg-[#222] border-blue-500/20 text-blue-400" : "bg-[#121212] border-[#222] text-[#444]"}`}>
              {useOcr ? "OCR Ativo (Docling)" : "OCR Desativado"}
            </button>
          </div>
          <div className="flex gap-2">
            <input type="file" ref={fileInputRef} onChange={e => setSelectedFiles(Array.from(e.target.files || []))} multiple className="hidden" />
            <button onClick={() => fileInputRef.current?.click()} className="flex-1 py-2.5 bg-[#252525] text-[#ccc] rounded-lg text-xs font-bold hover:bg-[#2a2a2a] border border-[#333]">Escolher Arquivos</button>
            {selectedFiles.length > 0 && !uploading && <button onClick={handleUpload} className="flex-1 py-2.5 bg-white text-black rounded-lg text-xs font-bold">Indexar {selectedFiles.length} Arquivos</button>}
          </div>
        </div>
        {(error || success) && <div className={`mt-4 p-3 rounded-lg border text-[11px] font-medium flex items-center gap-2 ${error ? "bg-red-500/5 border-red-500/10 text-red-400" : "bg-green-500/5 border-green-500/10 text-green-400"}`}><Check size={14} />{error || "Operação realizada com sucesso!"}</div>}
      </section>
    </div>
  );
}

function DocumentosTab() {
  const [stats, setStats] = useState({ total_files: 0, files: {} as any });
  const [loading, setLoading] = useState(true);
  const load = async () => { try { setStats(await getStats()); } catch(e){} finally { setLoading(false); } };
  useEffect(() => { load(); }, []);

  const del = async (n: string) => { if (confirm(`Deletar ${n}?`)) { await deleteDocument(n); load(); } };

  const handleClear = async () => {
    if (!confirm("⚠️ ATENÇÃO: Isso apagará TODO o conhecimento do Hermes. Deseja continuar?")) return;
    try { await clearDatabase(); load(); } catch(e){}
  };

  return (
    <div className="space-y-8">
      <h3 className="text-xl font-medium text-white">Biblioteca</h3>
      <div className="bg-[#1a1a1a] border border-[#333] rounded-xl overflow-hidden">
        <div className="divide-y divide-[#333] max-h-[300px] overflow-y-auto custom-scrollbar">
          {loading ? <div className="p-10 text-center text-[#444] animate-pulse text-xs">Carregando...</div> : 
            Object.keys(stats.files).length > 0 ? (
              Object.entries(stats.files).map(([name, info]: any, i) => (
                <div key={i} className="p-3 flex items-center justify-between group hover:bg-[#222] transition-colors">
                  <div className="flex items-center gap-3 truncate">
                    <div className="p-2 bg-[#222] rounded text-blue-400"><FileText size={14} /></div>
                    <div className="truncate"><div className="text-xs text-white truncate">{name}</div><div className="text-[9px] text-[#555] uppercase">{info.document_type} • {info.chunks} trechos</div></div>
                  </div>
                  <button onClick={() => del(name)} className="p-2 text-[#444] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"><Trash2 size={14} /></button>
                </div>
              ))
            ) : <div className="p-10 text-center text-[#333] text-xs">Nenhum documento indexado.</div>
          }
        </div>
      </div>

      <section className="pt-6 border-t border-[#333]/30">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h4 className="text-[11px] font-bold text-red-500/80 uppercase tracking-widest">Zona de Perigo</h4>
            <p className="text-[10px] text-[#555]">Apagar permanentemente toda a base de conhecimento.</p>
          </div>
          <button onClick={handleClear} className="px-3 py-1.5 bg-red-500/5 hover:bg-red-500/10 border border-red-500/10 text-red-500 text-[10px] font-bold rounded-lg transition-all uppercase">
            Resetar Banco
          </button>
        </div>
      </section>
    </div>
  );
}

function MotorTab() {
  const [cfg, setCfg] = useState({ provider: "", model: "" });
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => { getConfig().then(d => setCfg({ provider: d.llm_provider, model: d.model_name })); }, []);

  const save = async () => { 
    setSaving(true); setSuccess(false);
    try {
      await updateConfig(cfg.provider, cfg.model); 
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch(e) {}
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-medium text-white">Motor RAG</h3>
      <div className="bg-[#1a1a1a] border border-[#333] rounded-xl p-5 space-y-4">
        <div className="space-y-2">
          <label className="text-[10px] font-bold text-[#555] uppercase">Provedor</label>
          <select value={cfg.provider} onChange={e => setCfg({...cfg, provider: e.target.value})} className="w-full bg-[#121212] border border-[#222] rounded-lg px-3 py-2 text-sm text-white outline-none">
            <option value="Google Gemini">Google Gemini</option>
            <option value="Fireworks AI">Fireworks AI</option>
            <option value="OpenAI">OpenAI</option>
          </select>
        </div>
        <div className="pt-2">
          <button onClick={save} disabled={saving} className="w-full py-2.5 bg-white text-black rounded-lg text-xs font-bold hover:scale-[1.01] transition-all flex items-center justify-center gap-2">
            {saving ? <div className="w-3 h-3 border-2 border-black/20 border-t-black rounded-full animate-spin" /> : <Check size={14} />}
            {saving ? "Salvando..." : "Salvar Configurações"}
          </button>
        </div>
      </div>
      
      <AnimatePresence>
        {success && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="p-3 bg-green-500/5 border border-green-500/10 rounded-xl flex items-center gap-2 text-green-400 text-[11px] font-medium">
            <Check size={14} /> Configuração atualizada com sucesso!
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SettingItem({ icon, title, description, action }: any) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#333]/10">
      <div className="flex items-center gap-4">
        <div className="text-[#555]">{icon}</div>
        <div><div className="text-sm font-medium text-white">{title}</div><div className="text-xs text-[#555]">{description}</div></div>
      </div>
      {action}
    </div>
  );
}

function Select({ value }: { value: string }) {
  return <div className="bg-[#222] border border-[#333] rounded-lg px-3 py-1.5 text-xs text-white flex items-center gap-2 cursor-pointer">{value}</div>;
}
