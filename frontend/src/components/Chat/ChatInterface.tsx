"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, User, Bot, Paperclip, Mic, Sparkles, ChevronDown, Database, Tag, Check, Copy } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  subjects: string[];
  selectedSubject: string | null;
  onSelectSubject: (subject: string | null) => void;
}

export default function ChatInterface({
  messages,
  onSendMessage,
  isLoading,
  subjects,
  selectedSubject,
  onSelectSubject
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fecha dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput("");
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-[#212121] h-screen overflow-hidden">

      {/* 1. Header Discreto */}
      <header className="h-14 flex items-center px-6 justify-between bg-[#212121] z-20 flex-shrink-0">
        <div className="relative" ref={dropdownRef}>
          <button 
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-2 hover:bg-[#2f2f2f] px-3 py-1.5 rounded-lg transition-all group"
          >
            <Database size={16} className={selectedSubject ? "text-green-400" : "text-blue-400"} />
            <span className="text-xs font-medium text-[#999] uppercase tracking-widest group-hover:text-white">
              {selectedSubject ? selectedSubject : "Base Global"}
            </span>
            <ChevronDown size={14} className={`text-[#555] transition-transform ${isDropdownOpen ? "rotate-180" : ""}`} />
          </button>

          <AnimatePresence>
            {isDropdownOpen && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="absolute top-full left-0 mt-2 w-56 bg-[#171717] border border-[#333] rounded-xl shadow-2xl z-50 py-2 overflow-hidden"
              >
                <div className="px-3 py-1.5 text-[10px] font-bold text-[#555] uppercase tracking-widest">
                  Contexto de Análise
                </div>
                
                <button
                  onClick={() => {
                    onSelectSubject(null);
                    setIsDropdownOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 text-sm transition-colors hover:bg-[#2f2f2f] ${!selectedSubject ? "text-white" : "text-[#999]"}`}
                >
                  <div className="flex items-center gap-3">
                    <Database size={14} className={!selectedSubject ? "text-blue-400" : "text-[#444]"} />
                    <span>Base Global</span>
                  </div>
                  {!selectedSubject && <Check size={14} className="text-blue-400" />}
                </button>

                {subjects.map((subject) => (
                  <button
                    key={subject}
                    onClick={() => {
                      onSelectSubject(subject);
                      setIsDropdownOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-sm transition-colors hover:bg-[#2f2f2f] ${selectedSubject === subject ? "text-white" : "text-[#999]"}`}
                  >
                    <div className="flex items-center gap-3 truncate">
                      <Tag size={14} className={selectedSubject === subject ? "text-green-400" : "text-[#444]"} />
                      <span className="truncate">{subject || "Sem etiqueta"}</span>
                    </div>
                    {selectedSubject === subject && <Check size={14} className="text-green-400" />}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <div className="flex items-center gap-4 text-[#666]">
          <Sparkles size={16} className="hover:text-yellow-500 transition-colors cursor-pointer" />
        </div>
      </header>

      {/* 2. Messages Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto pt-4 pb-10 scroll-smooth custom-scrollbar"
      >
        <div className="max-w-[800px] mx-auto w-full px-4 space-y-8">
          <AnimatePresence initial={false}>
            {messages.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="h-[60vh] flex flex-col items-center justify-center text-white text-center"
              >
                <div className="w-16 h-16 bg-[#2f2f2f] rounded-2xl flex items-center justify-center mb-6 shadow-xl border border-[#333] overflow-hidden">
                  <img src="/assets/icon.svg" alt="Logo" className="w-10 h-10 object-contain" />
                </div>
                <h2 className="text-3xl font-semibold mb-3 tracking-tight">O que vamos analisar hoje?</h2>
                <p className="text-[#888] max-w-sm leading-relaxed">
                  Estou pronto para buscar insights na sua base de conhecimento.
                  {selectedSubject ? ` Focado em "${selectedSubject}".` : " Usando todo o conhecimento disponível."}
                </p>
              </motion.div>
            ) : (
              messages.map((msg, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`flex flex-col group ${msg.role === "assistant" ? "items-start" : "items-end"}`}
                >
                  <div className={`max-w-[85%] px-4 py-2.5 rounded-[22px] transition-all ${
                    msg.role === "user" 
                      ? "bg-[#2f2f2f] text-[#ececec] border border-[#333] hover:border-[#444]" 
                      : "text-[#ececec] px-0"
                  }`}>
                    <div className="text-[15px] leading-relaxed">
                      {msg.role === "assistant" ? (
                        <ReactMarkdown 
                          components={{
                            p: ({ ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                            ul: ({ ...props }) => <ul className="list-disc ml-5 mb-3 space-y-1" {...props} />,
                            ol: ({ ...props }) => <ol className="list-decimal ml-5 mb-3 space-y-1" {...props} />,
                            li: ({ ...props }) => <li className="pl-1" {...props} />,
                            strong: ({ ...props }) => <strong className="font-bold text-white" {...props} />,
                            code: ({ ...props }) => <code className="bg-[#171717] px-1.5 py-0.5 rounded text-blue-300 font-mono text-sm" {...props} />,
                            h1: ({ ...props }) => <h1 className="text-xl font-bold mb-4 mt-2" {...props} />,
                            h2: ({ ...props }) => <h2 className="text-lg font-bold mb-3 mt-2" {...props} />,
                            h3: ({ ...props }) => <h3 className="text-base font-bold mb-2 mt-1" {...props} />,
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      ) : (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      )}
                    </div>
                  </div>

                  {/* Botão de Copiar */}
                  <div className={`flex items-center mt-1.5 transition-opacity opacity-0 group-hover:opacity-100 ${
                    msg.role === "user" ? "mr-2" : "ml-0"
                  }`}>
                    <button
                      onClick={() => handleCopy(msg.content, idx)}
                      className="p-1.5 rounded-lg hover:bg-[#2f2f2f] text-[#666] hover:text-[#999] transition-all flex items-center gap-1.5"
                      title="Copiar mensagem"
                    >
                      {copiedIndex === idx ? (
                        <>
                          <Check size={14} className="text-green-500" />
                          <span className="text-[10px] font-medium text-green-500">Copiado!</span>
                        </>
                      ) : (
                        <Copy size={14} />
                      )}
                    </button>
                  </div>
                </motion.div>
              ))
            )}
          </AnimatePresence>

          {isLoading && (
            <div className="flex justify-start">
              <div className="flex gap-1.5 items-center px-0 py-3">
                <div className="w-1.5 h-1.5 bg-[#444] rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-[#444] rounded-full animate-bounce [animation-delay:0.2s]" />
                <div className="w-1.5 h-1.5 bg-[#444] rounded-full animate-bounce [animation-delay:0.4s]" />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. Input Area */}
      <div className="w-full bg-[#212121] pb-8 px-4 flex-shrink-0 border-t border-[#333]/30 pt-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-[800px] mx-auto relative"
        >
          <div className="bg-[#2f2f2f] border border-[#424242] rounded-[24px] p-1.5 flex items-end gap-2 shadow-2xl focus-within:border-[#666] transition-all group">
            <button
              type="button"
              className="p-3 text-[#888] hover:text-white transition-colors hover:bg-[#3f3f3f] rounded-full bg-transparent"
            >
              <Paperclip size={20} />
            </button>

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Envie uma mensagem para o Hermes..."
              rows={1}
              className="flex-1 bg-transparent border-none focus:ring-0 text-[#ececec] text-[15px] py-3 px-2 resize-none max-h-48 scrollbar-hide"
            />

            <div className="flex items-center gap-1.5 p-1">
              <button
                type="button"
                className="p-2 text-[#888] hover:text-white transition-colors hover:bg-[#3f3f3f] rounded-full bg-transparent"
              >
                <Mic size={20} />
              </button>
              <button
                disabled={!input.trim() || isLoading}
                type="submit"
                className={`p-2.5 rounded-full transition-all ${input.trim() && !isLoading
                    ? "bg-white text-black hover:scale-105 active:scale-95"
                    : "text-[#555] bg-[#3f3f3f]"
                  }`}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
          <p className="text-[10px] text-center text-[#555] mt-4 font-medium uppercase tracking-widest">
            Hermes Intel Engine v1.0
          </p>
        </form>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #333;
          border-radius: 10px;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}
