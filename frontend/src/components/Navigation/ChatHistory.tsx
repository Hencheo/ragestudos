"use client";

import React from "react";
import { MessageSquare, Trash2, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Session {
  id: string;
  title: string;
  summary?: string;
}

interface ChatHistoryProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  isCollapsed: boolean;
}

export default function ChatHistory({
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
  isCollapsed
}: ChatHistoryProps) {
  if (sessions.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 py-2">
      <AnimatePresence>
        {sessions.map((session) => (
          <motion.div
            key={session.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className={`group relative flex items-center ${
              isCollapsed ? "justify-center" : "px-3 mx-2"
            } py-2 rounded-lg cursor-pointer transition-all duration-200 ${
              currentSessionId === session.id && isCollapsed
                ? "bg-[#212121] shadow-sm" 
                : "hover:bg-[#212121]"
            }`}
            onClick={() => onSelectSession(session.id)}
          >
            {/* Ícone só aparece quando colapsado */}
            {isCollapsed && (
              <div className={`shrink-0 ${currentSessionId === session.id ? "text-blue-400" : "text-[#444] group-hover:text-[#666]"}`}>
                <MessageSquare size={14} />
              </div>
            )}

            {!isCollapsed && (
              <>
                <span className={`text-[13px] font-medium truncate flex-1 transition-colors duration-200 ${
                  currentSessionId === session.id ? "text-blue-400" : "text-[#ececec] group-hover:text-white"
                }`}>
                  {session.title}
                </span>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-[#3d3d3d] rounded-lg text-[#444] hover:text-red-400 transition-all ml-1"
                  title="Excluir conversa"
                >
                  <Trash2 size={14} />
                </button>
              </>
            )}

            {isCollapsed && currentSessionId === session.id && (
              <div className="absolute right-0 w-1 h-4 bg-blue-500 rounded-l-full" />
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
