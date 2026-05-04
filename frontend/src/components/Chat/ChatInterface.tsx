"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, User, Bot, Paperclip, Mic, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  selectedSubject: string | null;
}

export default function ChatInterface({
  messages,
  onSendMessage,
  isLoading,
  selectedSubject
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

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
      <header className="h-14 border-b border-[#333] flex items-center px-6 justify-between bg-[#212121] z-10 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs font-medium text-[#999] uppercase tracking-widest">
            {selectedSubject ? `Foco: ${selectedSubject}` : "Base Global"}
          </span>
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
                <div className="w-16 h-16 bg-[#2f2f2f] rounded-2xl flex items-center justify-center mb-6 shadow-xl border border-[#333]">
                  <Bot size={32} className="text-green-400" />
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
                  className={`flex gap-5 group ${
                    msg.role === "assistant" ? "items-start" : "items-start flex-row-reverse"
                  }`}
                >
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg border transition-all ${
                    msg.role === "assistant" 
                      ? "bg-[#2f2f2f] border-[#444] text-green-400" 
                      : "bg-[#ececec] border-white text-[#212121]"
                  }`}>
                    {msg.role === "assistant" ? <Bot size={20} /> : <User size={20} />}
                  </div>
                  
                  <div className={`max-w-[85%] px-1 pt-1.5 space-y-2 ${
                    msg.role === "user" ? "text-right" : "text-left"
                  }`}>
                    <div className="text-[#ececec] text-[15px] leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </AnimatePresence>

          {isLoading && (
            <div className="flex gap-5 items-center">
              <div className="w-9 h-9 rounded-xl bg-[#2f2f2f] border border-[#444] flex items-center justify-center text-green-400">
                <Bot size={20} className="animate-spin-slow" />
              </div>
              <div className="flex gap-1.5 items-center bg-[#2f2f2f] px-4 py-3 rounded-2xl border border-[#333]">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-bounce [animation-delay:0.4s]" />
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
                className={`p-2.5 rounded-full transition-all ${
                  input.trim() && !isLoading 
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
