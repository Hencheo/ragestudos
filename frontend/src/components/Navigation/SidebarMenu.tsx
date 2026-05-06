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
import ChatHistory from "./ChatHistory";

interface Session {
  id: string;
  title: string;
  summary?: string;
}

interface SidebarMenuProps {
  subjects: string[];
  selectedSubject: string | null;
  onSelectSubject: (subject: string | null) => void;
  onNewChat: () => void;
  onOpenSettings: () => void;
  onOpenUpload: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
}

export default function SidebarMenu({
  subjects,
  selectedSubject,
  onSelectSubject,
  onNewChat,
  onOpenSettings,
  onOpenUpload,
  isCollapsed,
  onToggleCollapse,
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession
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
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={onNewChat}
          className={`flex items-center ${isCollapsed ? "justify-center" : "gap-2.5 px-3"} py-2 border border-[#333] rounded-lg bg-[#171717] hover:bg-[#212121] transition-all text-[13px] font-medium text-[#ececec] w-full`}
        >
          <Plus size={16} className="text-white shrink-0" />
          {!isCollapsed && <span>Nova Conversa</span>}
        </motion.button>
      </div>

      {/* 2. MIDDLE: Histórico de Conversas */}
      <div className="flex-1 overflow-y-auto mt-2 custom-scrollbar">
        {sessions.length > 0 && (
          <div className="mx-4 h-[1px] bg-[#222] mb-4 opacity-50" />
        )}
        
        <ChatHistory 
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={onSelectSession}
          onDeleteSession={onDeleteSession}
          isCollapsed={isCollapsed}
        />

        {subjects.length === 0 && sessions.length === 0 && !isCollapsed && (
          <div className="px-6 py-10 text-[11px] text-[#333] text-center uppercase tracking-[0.2em] font-bold opacity-50">
            Limpo
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
