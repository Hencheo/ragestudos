
"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, Settings, Database, Cpu, Trash2, Upload, 
  Check, AlertCircle, FileText, Globe, Palette 
} from "lucide-react";
import { uploadFiles, getUploadStatus, cancelUpload, getStats, deleteDocument, clearDatabase, getConfig, updateConfig } from "@/lib/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  subjects: string[];
  initialTab?: Tab;
}

type Tab = "geral" | "dados" | "documentos" | "motor";

export default function SettingsModal({ isOpen, onClose, subjects, initialTab = "geral" }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>(initialTab);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sincroniza a aba quando o modal abre
  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
    }
  }, [isOpen, initialTab]);
  
  // Fecha ao apertar ESC
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
        {/* Overlay com Blur */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        />

        {/* Modal Content */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-[840px] h-[600px] bg-[#171717] border border-[#333] rounded-2xl shadow-2xl overflow-hidden flex"
        >
          {/* SIDEBAR DO MODAL */}
          <aside className="w-64 bg-[#121212] border-r border-[#333] p-4 flex flex-col gap-1">
            <div className="px-3 py-4 mb-2">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Settings size={20} className="text-[#888]" />
                Configurações
              </h2>
            </div>

            <TabButton 
              active={activeTab === "geral"} 
              onClick={() => setActiveTab("geral")}
              icon={<Settings size={18} />}
              label="Geral"
            />
            <TabButton 
              active={activeTab === "dados"} 
              onClick={() => setActiveTab("dados")}
              icon={<Upload size={18} />}
              label="Upload de Dados"
            />
            <TabButton 
              active={activeTab === "documentos"} 
              onClick={() => setActiveTab("documentos")}
              icon={<FileText size={18} />}
              label="Documentos"
            />
            <TabButton 
              active={activeTab === "motor"} 
              onClick={() => setActiveTab("motor")}
              icon={<Cpu size={18} />}
              label="Motor RAG"
            />
          </aside>

          {/* ÁREA DE CONTEÚDO */}
          <div className="flex-1 flex flex-col bg-[#171717]">
            <header className="h-16 flex items-center justify-end px-6 shrink-0 border-b border-[#333]/30">
              <button 
                onClick={onClose}
                className="p-2 text-[#666] hover:text-white hover:bg-[#2f2f2f] rounded-xl transition-all"
                title="Fechar (Esc)"
              >
                <X size={20} />
              </button>
            </header>

            <main className="flex-1 overflow-y-auto p-8 pt-6">
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
    <button
      onClick={onClick}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all font-medium text-sm ${
        active 
          ? "bg-[#2f2f2f] text-white" 
          : "text-[#999] hover:bg-[#1f1f1f] hover:text-white"
      }`}
    >
      <span className={active ? "text-white" : "text-[#555]"}>{icon}</span>
      {label}
    </button>
  );
}

// --- SUB-COMPONENTES DAS ABAS ---

function GeralTab() {
  return (
    <div className="space-y-8">
      <section>
        <h3 className="text-xl font-medium text-white mb-6">Geral</h3>
        <div className="space-y-6">
          <SettingItem 
            icon={<Palette size={18} />} 
            title="Aparência" 
            description="Escolha como o Hermes se parece para você."
            action={<Select value="Escuro" options={["Escuro", "Claro", "Sistema"]} />}
          />
          <SettingItem 
            icon={<Globe size={18} />} 
            title="Idioma" 
            description="Idioma da interface e respostas padrão."
            action={<Select value="Português (BR)" options={["Português (BR)", "English"]} />}
          />
        </div>
      </section>
    </div>
  );
}

function UploadTab() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [subject, setSubject] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [useOcr, setUseOcr] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      setSelectedFiles(Array.from(files));
      setError(null);
      setSuccess(false);
      setProgress(0);
      setStatusMessage("");
    }
  };

  const pollStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const statusData = await getUploadStatus(taskId);
        setProgress(statusData.progress);
        setStatusMessage(statusData.message);

        if (statusData.status === "completed") {
          clearInterval(interval);
          setUploading(false);
          setSuccess(true);
          setSelectedFiles([]);
          setSubject("");
          setCurrentTaskId(null);
          setTimeout(() => {
            setSuccess(false);
            setProgress(0);
            setStatusMessage("");
          }, 5000);
        } else if (statusData.status === "failed" || statusData.status === "cancelled") {
          clearInterval(interval);
          setUploading(false);
          if (statusData.status === "cancelled") {
            setError("Processamento interrompido pelo usuário.");
          } else {
            setError(statusData.message || "Falha no processamento");
          }
          setCurrentTaskId(null);
        }
      } catch (err) {
        console.error("Erro ao consultar status:", err);
        clearInterval(interval);
        setUploading(false);
        setError("Erro ao monitorar o progresso.");
      }
    }, 1000);
  };

  const handleConfirmUpload = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setError(null);
    setSuccess(false);
    setProgress(0);
    setStatusMessage("Enviando arquivos...");

    try {
      const data = await uploadFiles(selectedFiles, subject, useOcr);
      if (data.success && data.task_id) {
        setCurrentTaskId(data.task_id);
        pollStatus(data.task_id);
      } else {
        throw new Error(data.message || "Falha ao iniciar upload");
      }
    } catch (err: any) {
      setError(err.message || "Erro ao enviar arquivos.");
      setUploading(false);
    }
  };

  const handleCancel = async () => {
    if (!currentTaskId) return;
    try {
      await cancelUpload(currentTaskId);
      setStatusMessage("Cancelamento solicitado...");
    } catch (err) {
      console.error("Erro ao cancelar:", err);
      setError("Erro ao solicitar cancelamento.");
    }
  };

  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-medium text-white">Upload de Conhecimento</h3>
          {uploading && (
             <button 
               onClick={handleCancel}
               title="Clique para interromper o processamento atual"
               className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 border border-red-500/20 rounded-full hover:bg-red-500/20 transition-all group/stop"
             >
               <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse group-hover/stop:scale-125 transition-transform" />
               <span className="text-[10px] font-bold text-red-400 uppercase tracking-tighter">Interromper Processo</span>
             </button>
          )}
        </div>

        <div className="bg-[#1f1f1f] border border-[#333] rounded-2xl p-6 mb-8 space-y-6 relative overflow-hidden">
          {uploading && (
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              className="absolute top-0 left-0 h-1 bg-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.5)] z-10"
            />
          )}

          <div className="space-y-2">
            <label className="text-xs font-bold text-[#666] uppercase tracking-widest">Assunto / Etiqueta de Contexto</label>
            <input 
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Ex: Currículos, Finanças, Projetos..."
              disabled={uploading}
              className="w-full bg-[#171717] border border-[#333] rounded-xl px-4 py-2.5 text-sm text-white focus:border-blue-500/50 transition-all outline-none disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-between p-4 bg-[#171717] rounded-xl border border-[#333]">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${useOcr ? "bg-blue-500/10 text-blue-400" : "bg-[#2a2a2a] text-[#555]"}`}>
                <Cpu size={16} />
              </div>
              <div>
                <div className="text-sm font-medium text-white">Usar OCR (Docling AI)</div>
                <div className="text-[10px] text-[#555] uppercase tracking-tighter">Ative para ler documentos escaneados ou imagens</div>
              </div>
            </div>
            <button 
              onClick={() => setUseOcr(!useOcr)}
              disabled={uploading}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${useOcr ? "bg-blue-600" : "bg-[#333]"}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${useOcr ? "translate-x-6" : "translate-x-1"}`} />
            </button>
          </div>

          <div className="flex items-center gap-4">
            <input type="file" ref={fileInputRef} onChange={onFileSelect} multiple accept=".pdf,.txt" className="hidden" disabled={uploading} />
            <button 
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-2 px-4 py-2 bg-[#2a2a2a] text-white rounded-lg text-sm font-medium hover:bg-[#333] transition-all disabled:opacity-50"
            >
              <Upload size={16} />
              Selecionar Arquivos (.pdf, .txt)
            </button>
            {selectedFiles.length > 0 && !uploading && (
              <span className="text-xs text-[#666]">{selectedFiles.length} arquivo(s) selecionado(s)</span>
            )}
          </div>

          {(selectedFiles.length > 0 || uploading) && (
            <div className="pt-4 border-t border-[#333]/50 space-y-4">
              {uploading && (
                <div className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                    <span className="text-blue-400 animate-pulse">{statusMessage}</span>
                    <span className="text-[#666]">{progress}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-[#171717] rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${progress}%` }} className="h-full bg-gradient-to-r from-blue-600 to-blue-400" />
                  </div>
                </div>
              )}
              {!uploading && (
                <button onClick={handleConfirmUpload} className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white text-black rounded-xl text-sm font-bold transition-all hover:scale-[1.01] active:scale-[0.98]">
                  <Check size={18} />
                  Confirmar e Indexar Agora
                </button>
              )}
            </div>
          )}
        </div>

        {error && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-4 p-4 bg-red-500/5 border border-red-500/20 rounded-2xl text-red-400 text-xs flex items-center gap-3">
            <AlertCircle size={18} className="shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}

        {success && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-4 p-4 bg-green-500/5 border border-green-500/20 rounded-2xl text-green-400 text-xs flex items-center gap-3">
            <Check size={18} className="shrink-0" />
            <span>Arquivos indexados com sucesso!</span>
          </motion.div>
        )}
      </section>
    </div>
  );
}

function DocumentosTab() {
  const [dbStats, setDbStats] = useState<{ 
    total_files: number, 
    files: Record<string, { 
      subject: string, 
      document_type: string, 
      case_number: string, 
      chunks: number 
    }> 
  }>({ total_files: 0, files: {} });
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const data = await getStats();
      setDbStats(data);
    } catch (err) {
      console.error("Erro ao buscar stats:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleDeleteFile = async (fileName: string) => {
    if (!confirm(`Deseja realmente remover o arquivo "${fileName}"?`)) return;
    try {
      await deleteDocument(fileName);
      fetchStats();
    } catch (err) {
      console.error(err);
      alert("Erro ao deletar arquivo.");
    }
  };

  const handleClearDatabase = async () => {
    if (!confirm("⚠️ ATENÇÃO: Isso apagará TODO o conhecimento do Hermes. Deseja continuar?")) return;
    try {
      await clearDatabase();
      fetchStats();
      alert("Base de conhecimento limpa com sucesso.");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-8">
      <section>
        <h3 className="text-xl font-medium text-white mb-6">Documentos Indexados</h3>
        <div className="bg-[#1f1f1f] border border-[#333] rounded-2xl overflow-hidden">
          <div className="px-4 py-3 bg-[#262626] border-b border-[#333] text-[10px] font-bold text-[#666] uppercase tracking-widest flex justify-between">
            <span>Biblioteca Atual</span>
            <span className="text-blue-400">{dbStats.total_files} arquivos</span>
          </div>
          <div className="divide-y divide-[#333] max-h-[380px] overflow-y-auto custom-scrollbar">
            {loading ? (
              <div className="p-12 text-center text-[#555] animate-pulse">Carregando biblioteca...</div>
            ) : Object.keys(dbStats.files).length > 0 ? (
              Object.entries(dbStats.files).map(([name, info], i) => (
                <div key={i} className="px-4 py-4 flex items-center justify-between group hover:bg-[#252525] transition-colors">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="p-2 bg-[#2a2a2a] rounded-lg text-blue-400 shrink-0">
                      <FileText size={16} />
                    </div>
                    <div className="truncate">
                      <div className="text-sm font-medium text-white truncate" title={name}>{name}</div>
                      <div className="text-[10px] text-[#666] flex gap-2 items-center mt-0.5">
                        <span className="bg-[#2a2a2a] px-1.5 py-0.5 rounded text-blue-300 font-bold uppercase tracking-tighter">{info.document_type || "Geral"}</span>
                        <span className="truncate max-w-[120px]">{info.case_number !== "Não identificado" ? info.case_number : "Sem Nº Processo"}</span>
                        <span className="text-[#333]">•</span>
                        <span>{info.chunks} trechos</span>
                      </div>
                    </div>
                  </div>
                  <button onClick={() => handleDeleteFile(name)} className="p-2 text-[#444] hover:text-red-400 hover:bg-red-400/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all shrink-0">
                    <Trash2 size={16} />
                  </button>
                </div>
              ))
            ) : (
              <div className="p-12 text-center text-[#555]">
                <Database size={48} className="mx-auto mb-4 opacity-10" />
                <p>Nenhum documento encontrado.</p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="p-4 bg-red-500/5 border border-red-500/20 rounded-2xl">
        <h4 className="text-sm font-semibold text-red-400 mb-1 flex items-center gap-2">
          <AlertCircle size={14} />
          Zona de Perigo
        </h4>
        <p className="text-xs text-red-400/60 mb-4">Apagar todos os dados da base é uma ação irreversível.</p>
        <button onClick={handleClearDatabase} className="text-xs font-bold text-red-500 hover:underline">
          Limpar toda a base de conhecimento
        </button>
      </section>
    </div>
  );
}

function MotorTab() {
  const [llmProvider, setLlmProvider] = useState("Google Gemini");
  const [modelName, setModelName] = useState("gemini-2.5-flash");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    getConfig()
      .then(data => {
        setLlmProvider(data.llm_provider);
        setModelName(data.model_name);
      })
      .catch(console.error);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await updateConfig(llmProvider, modelName);
      setMessage({ type: 'success', text: "Configuração do motor atualizada com sucesso!" });
    } catch (err) {
      setMessage({ type: 'error', text: "Erro ao salvar. Verifique o backend." });
    } finally {
      setSaving(false);
    }
  };

  const providers = [
    { name: "Google Gemini", models: ["gemini-2.5-flash", "gemini-1.5-pro"] },
    { name: "Fireworks AI", models: ["accounts/fireworks/routers/kimi-k2p5-turbo"] },
    { name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini"] }
  ];

  return (
    <div className="space-y-8">
      <section>
        <h3 className="text-xl font-medium text-white mb-6">Motor de Inteligência</h3>
        <div className="bg-[#1f1f1f] border border-[#333] rounded-2xl p-6 space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-bold text-[#666] uppercase tracking-widest">Provedor de LLM</label>
            <select value={llmProvider} onChange={(e) => {
              const p = e.target.value;
              setLlmProvider(p);
              const firstModel = providers.find(pr => pr.name === p)?.models[0];
              if (firstModel) setModelName(firstModel);
            }} className="w-full bg-[#171717] border border-[#333] rounded-xl px-4 py-2.5 text-sm text-white outline-none focus:border-blue-500/50">
              {providers.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-[#666] uppercase tracking-widest">Modelo Específico</label>
            <select value={modelName} onChange={(e) => setModelName(e.target.value)} className="w-full bg-[#171717] border border-[#333] rounded-xl px-4 py-2.5 text-sm text-white outline-none focus:border-blue-500/50">
              {providers.find(p => p.name === llmProvider)?.models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div className="pt-4 border-t border-[#333]/50">
            <button onClick={handleSave} disabled={saving} className={`w-full py-3 rounded-xl text-sm font-bold transition-all ${saving ? "bg-[#333] text-[#555]" : "bg-white text-black hover:scale-[1.01]"}`}>
              {saving ? "Salvando Alterações..." : "Aplicar Configurações do Motor"}
            </button>
          </div>
        </div>
        {message && (
          <div className={`mt-4 p-4 rounded-2xl text-xs flex items-center gap-3 ${message.type === 'success' ? "bg-green-500/5 border border-green-500/20 text-green-400" : "bg-red-500/5 border border-red-500/20 text-red-400"}`}>
            {message.type === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}
            <span>{message.text}</span>
          </div>
        )}
      </section>
    </div>
  );
}

function SettingItem({ icon, title, description, action }: { icon: React.ReactNode, title: string, description: string, action: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        <div className="text-[#666]">{icon}</div>
        <div>
          <div className="text-sm font-medium text-white">{title}</div>
          <div className="text-xs text-[#555]">{description}</div>
        </div>
      </div>
      <div>{action}</div>
    </div>
  );
}

function Select({ value, options }: { value: string, options: string[] }) {
  return (
    <div className="bg-[#2a2a2a] border border-[#333] rounded-lg px-3 py-1.5 text-sm text-white flex items-center gap-2 cursor-pointer hover:bg-[#333] transition-all">
      {value}
      <ChevronDown size={14} className="text-[#666]" />
    </div>
  );
}

function ChevronDown({ size, className }: { size: number, className: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m6 9 6 6 6-6"/>
    </svg>
  );
}
