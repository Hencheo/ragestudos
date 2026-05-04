"use client";

import React from "react";
import {
  Plus,
  MessageSquare,
  Database,
  Settings,
  Upload,
  BookOpen,
  Activity,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen
} from "lucide-react";
import { motion } from "framer-motion";

interface SidebarMenuProps {
  subjects: string[];
  selectedSubject: string | null;
  onSelectSubject: (subject: string | null) => void;
  onNewChat: () => void;
  onOpenSettings: () => void;
  onOpenUpload: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export default function SidebarMenu({
  subjects,
  selectedSubject,
  onSelectSubject,
  onNewChat,
  onOpenSettings,
  onOpenUpload,
  isCollapsed,
  onToggleCollapse
}: SidebarMenuProps) {
  return (
    <aside 
      className={`${isCollapsed ? "w-[68px]" : "w-[260px]"} bg-[#171717] h-screen flex flex-col border-r border-[#333] text-[#ececec] select-none transition-all duration-300 ease-in-out relative group/sidebar`}
    >
      
      {/* 1. TOP: Header com Logo e Toggle */}
      <div className={`p-4 flex items-center ${isCollapsed ? "justify-center" : "justify-between"} relative h-16`}>
        <div className="relative group cursor-pointer" onClick={isCollapsed ? onToggleCollapse : undefined}>
          {/* Logo */}
          <img 
            src="/assets/icon.svg" 
            alt="Hermes Icon" 
            className={`w-8 h-8 opacity-90 transition-all duration-300 ${isCollapsed ? "group-hover:opacity-0" : "opacity-100"}`} 
          />
          
          {/* Ícone de Abrir (aparece no hover quando colapsado) */}
          {isCollapsed && (
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <PanelLeftOpen size={20} className="text-[#999] hover:text-white" />
            </div>
          )}
        </div>

        {/* Botão de Fechar (apenas quando expandido) */}
        {!isCollapsed && (
          <button 
            onClick={onToggleCollapse}
            className="p-1.5 rounded-lg hover:bg-[#2f2f2f] text-[#666] hover:text-[#ccc] transition-colors"
          >
            <PanelLeftClose size={18} />
          </button>
        )}
      </div>

      {/* 2. ACTIONS: Nova Conversa */}
      <div className="p-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onNewChat}
          className={`flex items-center ${isCollapsed ? "justify-center" : "gap-3 px-3"} py-3 border border-[#333] rounded-xl bg-[#171717] hover:bg-[#2f2f2f] transition-all text-sm font-medium shadow-sm text-[#ececec] w-full`}
        >
          <Plus size={18} className="text-white shrink-0" />
          {!isCollapsed && <span>Nova Conversa</span>}
        </motion.button>
      </div>

      {/* 2. MIDDLE: Contextos / Assuntos - Agora movidos para o dropdown do header */}
      <div className="flex-1 overflow-y-auto px-3 mt-4 space-y-1 custom-scrollbar">

        {/* Assuntos agora ficam no dropdown do header no ChatInterface */}

        {/* Assuntos agora ficam no dropdown do header no ChatInterface */}

        {subjects.length === 0 && (
          <div className="px-3 py-4 text-[12px] text-[#444] text-center italic">
            Nenhum assunto indexado.
          </div>
        )}
      </div>

      {/* 4. BOTTOM: Gestão e Sistema */}
      <div className={`p-3 mt-auto border-t border-[#333] space-y-1 bg-[#171717]`}>
        {!isCollapsed && (
          <div className="text-[10px] font-bold text-[#555] px-3 uppercase tracking-[0.1em] mb-2 pt-2">
            Biblioteca
          </div>
        )}

        <button
          onClick={onOpenUpload}
          className={`w-full group flex items-center ${isCollapsed ? "justify-center" : "gap-3 px-3"} py-2.5 rounded-lg text-sm text-[#999] hover:bg-[#222] hover:text-[#ccc] transition-all bg-transparent`}
          title={isCollapsed ? "Importar Dados" : ""}
        >
          <div className="bg-[#222] p-1.5 rounded group-hover:bg-[#333] shrink-0">
            <Upload size={14} />
          </div>
          {!isCollapsed && <span>Importar Dados</span>}
        </button>

        <button
          className={`w-full group flex items-center ${isCollapsed ? "justify-center" : "gap-3 px-3"} py-2.5 rounded-lg text-sm text-[#999] hover:bg-[#222] hover:text-[#ccc] transition-all bg-transparent`}
          title={isCollapsed ? "Gerenciar Base" : ""}
        >
          <div className="bg-[#222] p-1.5 rounded group-hover:bg-[#333] shrink-0">
            <BookOpen size={14} />
          </div>
          {!isCollapsed && <span>Gerenciar Base</span>}
        </button>

        <div className="pt-2">
          <button
            onClick={onOpenSettings}
            className={`w-full flex items-center ${isCollapsed ? "justify-center" : "gap-3 px-3"} py-3 rounded-xl text-sm text-[#ccc] hover:bg-[#2f2f2f] transition-all mt-2 border border-transparent hover:border-[#444] bg-transparent`}
            title={isCollapsed ? "Configurações" : ""}
          >
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-[#333] to-[#444] flex items-center justify-center text-[10px] font-bold shrink-0">
              H
            </div>
            {!isCollapsed && <span className="flex-1 text-left font-medium">Configurações</span>}
            {!isCollapsed && <Settings size={14} className="opacity-40" />}
          </button>
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #333;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #444;
        }
      `}</style>
    </aside>
  );
}
