"use client";

import React, { useState, useEffect } from "react";
import SidebarMenu from "@/components/Navigation/SidebarMenu";
import ChatInterface from "@/components/Chat/ChatInterface";
import SettingsModal from "@/components/Settings/SettingsModal";
import { queryHermes, getStats } from "@/lib/api";

export default function Home() {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<"geral" | "dados" | "motor">("geral");

  // Carrega assuntos iniciais
  useEffect(() => {
    async function loadStats() {
      try {
        const stats = await getStats();
        const uniqueSubjects = Array.from(new Set(Object.values(stats.files || {}).map((f: any) => f.subject))) as string[];
        setSubjects(uniqueSubjects);
      } catch (err) {
        console.error("Erro ao carregar stats:", err);
      }
    }
    loadStats();
  }, []);

  const handleSendMessage = async (text: string) => {
    // Adiciona msg do usuário
    const newMessages = [...messages, { role: "user", content: text } as const];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const data = await queryHermes(text, selectedSubject || undefined);
      setMessages([...newMessages, { role: "assistant", content: data.response }]);
    } catch (err) {
      setMessages([...newMessages, { role: "assistant", content: "Erro ao conectar com o servidor." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex h-screen w-full bg-[#212121] overflow-hidden">
      <SidebarMenu 
        subjects={subjects}
        selectedSubject={selectedSubject}
        onSelectSubject={setSelectedSubject}
        onNewChat={() => setMessages([])}
        onOpenSettings={() => { setSettingsTab("geral"); setIsSettingsOpen(true); }}
        onOpenUpload={() => { setSettingsTab("dados"); setIsSettingsOpen(true); }}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
      />
      <ChatInterface 
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        subjects={subjects}
        selectedSubject={selectedSubject}
        onSelectSubject={setSelectedSubject}
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
