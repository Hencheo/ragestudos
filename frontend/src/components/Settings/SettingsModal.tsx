
"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, Settings, Database, Cpu, Trash2, Upload, 
  Check, AlertCircle, FileText, Globe, Palette 
} from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  subjects: string[];
}

type Tab = "geral" | "dados" | "motor";

export default function SettingsModal({ isOpen, onClose, subjects }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>("geral");
  const [isUploading, setIsUploading] = useState(false);
  
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
          {/* Botão Fechar Mobile/Topo */}
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 text-[#666] hover:text-white hover:bg-[#2f2f2f] rounded-lg transition-all z-50"
          >
            <X size={20} />
          </button>

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
              icon={<Database size={18} />}
              label="Base de Dados"
            />
            <TabButton 
              active={activeTab === "motor"} 
              onClick={() => setActiveTab("motor")}
              icon={<Cpu size={18} />}
              label="Motor RAG"
            />
          </aside>

          {/* CONTEÚDO PRINCIPAL */}
          <main className="flex-1 overflow-y-auto p-8 bg-[#171717]">
            {activeTab === "geral" && <GeralTab />}
            {activeTab === "dados" && <DadosTab subjects={subjects} />}
            {activeTab === "motor" && <MotorTab />}
          </main>
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

function DadosTab({ subjects }: { subjects: string[] }) {
  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-medium text-white">Base de Dados</h3>
          <button className="flex items-center gap-2 px-4 py-2 bg-white text-black rounded-full text-sm font-semibold hover:bg-[#eee] transition-all">
            <Upload size={16} />
            Importar PDF
          </button>
        </div>

        <div className="bg-[#1f1f1f] border border-[#333] rounded-2xl overflow-hidden">
          <div className="px-4 py-3 bg-[#262626] border-b border-[#333] text-[10px] font-bold text-[#666] uppercase tracking-widest">
            Documentos Indexados
          </div>
          <div className="divide-y divide-[#333]">
            {subjects.length > 0 ? (
              subjects.map((sub, i) => (
                <div key={i} className="px-4 py-4 flex items-center justify-between group hover:bg-[#252525] transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-[#2a2a2a] rounded-lg text-blue-400">
                      <FileText size={16} />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{sub || "Sem Assunto"}</div>
                      <div className="text-[11px] text-[#555]">PDF • Processado via Docling</div>
                    </div>
                  </div>
                  <button className="p-2 text-[#444] hover:text-red-400 hover:bg-red-400/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all">
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
        <button className="text-xs font-bold text-red-500 hover:underline">
          Limpar toda a base de conhecimento
        </button>
      </section>
    </div>
  );
}

function MotorTab() {
  return (
    <div className="space-y-8">
      <section>
        <h3 className="text-xl font-medium text-white mb-6">Motor RAG</h3>
        <div className="space-y-6">
          <SettingItem 
            icon={<Cpu size={18} />} 
            title="Modelo de Resposta" 
            description="O cérebro por trás das respostas."
            action={<Select value="Gemini 2.5 Flash" options={["Gemini 2.5 Flash", "Gemini 3.1 Pro"]} />}
          />
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-[#999]">Temperatura</span>
              <span className="text-sm text-white font-mono">0.7</span>
            </div>
            <input type="range" className="w-full accent-white h-1.5 bg-[#333] rounded-lg appearance-none cursor-pointer" />
            <p className="text-[10px] text-[#555]">Valores mais baixos são mais precisos, valores altos mais criativos.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

// --- UTILS INTERNOS ---

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
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="m6 9 6 6 6-6"/>
    </svg>
  );
}
