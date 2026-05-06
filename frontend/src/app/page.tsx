"use client";

import React, { useState, useEffect } from "react";
import SidebarMenu from "@/components/Navigation/SidebarMenu";
import ChatInterface from "@/components/Chat/ChatInterface";
import SettingsModal from "@/components/Settings/SettingsModal";
import { queryHermes, getStats, getSessions, clearDatabase } from "@/lib/api";

export default function Home() {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<"geral" | "dados" | "motor">("geral");
  const [sessionId, setSessionId] = useState<string>(() => `web_${Math.random().toString(36).substring(7)}`);

  // Carrega assuntos e sessões iniciais
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [stats, sessionList] = await Promise.all([getStats(), getSessions()]);
        const uniqueSubjects = Array.from(new Set(Object.values(stats.files || {}).map((f: any) => f.subject))) as string[];
        setSubjects(uniqueSubjects);
        setSessions(sessionList);
      } catch (err) {
        console.error("Erro ao carregar dados iniciais:", err);
      }
    }
    loadInitialData();
  }, []);

  const refreshSessions = async () => {
    try {
      const sessionList = await getSessions();
      setSessions(sessionList);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (text: string) => {
    // Adiciona msg do usuário
    const newMessages = [...messages, { role: "user", content: text } as const];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const data = await queryHermes(text, selectedSubject || undefined, sessionId);
      setMessages([...newMessages, { role: "assistant", content: data.response }]);
      // Atualiza lista de sessões para pegar possíveis novos resumos
      refreshSessions();
    } catch (err) {
      setMessages([...newMessages, { role: "assistant", content: "Erro ao conectar com o servidor." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSession = (id: string) => {
    setSessionId(id);
    setMessages([{ 
      role: "assistant", 
      content: `Contexto da conversa **${id}** carregado da memória persistente. Como posso continuar ajudando?` 
    }]);
  };

  const handleDeleteSession = async (id: string) => {
    if (!confirm("Excluir esta conversa permanentemente?")) return;
    try {
      await clearDatabase({ session_id: id });
      setSessions(prev => prev.filter(s => s.id !== id));
      if (sessionId === id) {
        setMessages([]);
        setSessionId(`web_${Math.random().toString(36).substring(7)}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <main className="flex h-screen w-full bg-[#212121] overflow-hidden">
      <SidebarMenu 
        subjects={subjects}
        selectedSubject={selectedSubject}
        onSelectSubject={setSelectedSubject}
        onNewChat={() => {
          setMessages([]);
          setSessionId(`web_${Math.random().toString(36).substring(7)}`);
        }}
        onOpenSettings={() => { setSettingsTab("geral"); setIsSettingsOpen(true); }}
        onOpenUpload={() => { setSettingsTab("dados"); setIsSettingsOpen(true); }}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        sessions={sessions}
        currentSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      />
      <ChatInterface 
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        subjects={subjects}
        selectedSubject={selectedSubject}
        onSelectSubject={setSelectedSubject}
        onOpenUpload={() => { setSettingsTab("dados"); setIsSettingsOpen(true); }}
      />
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
        subjects={subjects}
        initialTab={settingsTab}
      />
    </main>
  );
}
