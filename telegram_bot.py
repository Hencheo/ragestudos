import os
import logging
import httpx
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("hermes.telegram")

# Configurações
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("HERMES_API_URL", "http://localhost:8000")

if not TOKEN:
    logger.warning("TELEGRAM_BOT_TOKEN não encontrado no .env. O bot não iniciará.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem de boas-vindas."""
    user = update.effective_user
    welcome_text = (
        f"Olá {user.first_name}! Eu sou o **Hermes Jurídico**, seu assistente de IA.\n\n"
        "Posso ajudar você a:\n"
        "🔍 **Consultar Teses**: Encontrar argumentos em petições antigas.\n"
        "📄 **Analisar Contratos**: Tirar dúvidas sobre cláusulas e riscos.\n"
        "📚 **Base de Conhecimento**: Responder sobre leis e jurisprudência.\n\n"
        "Basta me enviar uma pergunta ou um arquivo PDF para indexação."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de ajuda."""
    help_text = (
        "📌 **Comandos Disponíveis:**\n"
        "/start - Iniciar conversa\n"
        "/help - Ver esta ajuda\n"
        "/stats - Ver estatísticas da base\n\n"
        "💡 **Como usar:**\n"
        "- Envie qualquer pergunta em texto.\n"
        "- Envie um arquivo PDF para adicioná-lo à minha memória."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Consulta estatísticas do backend."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/stats", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                stats_text = (
                    "📊 **Estatísticas da Base:**\n"
                    f"Total de arquivos: {data.get('total_files', 0)}\n\n"
                    "Arquivos recentes:\n"
                )
                files = data.get("files", {})
                for fname, info in list(files.items())[:5]:
                    stats_text += f"- {fname} ({info.get('subject', 'Sem Assunto')})\n"
                
                await update.message.reply_text(stats_text, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Erro ao consultar backend.")
    except Exception as e:
        logger.error(f"Erro no stats: {e}")
        await update.message.reply_text("⚠️ O servidor Hermes está offline ou inacessível.")

async def clear_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpa a base de dados."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_URL}/clear", timeout=10.0)
            if response.status_code == 200:
                await update.message.reply_text("Broom! 🧹 A base de dados foi limpa com sucesso.")
            else:
                await update.message.reply_text("❌ Erro ao limpar a base.")
    except Exception as e:
        logger.error(f"Erro no clear: {e}")
        await update.message.reply_text("⚠️ Falha de comunicação com o servidor.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trata mensagens de texto (queries)."""
    question = update.message.text
    if not question:
        return

    # Feedback visual de que o bot está processando
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        async with httpx.AsyncClient() as client:
            # Chama o endpoint de query do backend
            # O backend espera Form data para question e subject
            response = await client.post(
                f"{API_URL}/query",
                data={"question": question},
                timeout=60.0
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "Não obtive resposta.")
                # Envia a resposta (que já deve vir formatada em Markdown)
                await update.message.reply_text(answer, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ O servidor encontrou um problema ao processar sua pergunta.")
    except Exception as e:
        logger.error(f"Erro na query: {e}")
        await update.message.reply_text("⚠️ Falha de comunicação com o cérebro do Hermes. Verifique se o backend está rodando.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trata upload de documentos."""
    doc = update.message.document
    if not doc.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("⚠️ Por favor, envie apenas arquivos PDF.")
        return

    await update.message.reply_text(f"📥 Recebi **{doc.file_name}**. Iniciando processamento e indexação...")

    try:
        # Download do arquivo do Telegram
        new_file = await context.bot.get_file(doc.file_id)
        file_content = await new_file.download_as_bytearray()

        # Envia para o backend
        async with httpx.AsyncClient() as client:
            files = {'files': (doc.file_name, bytes(file_content), 'application/pdf')}
            data = {'subject': 'Telegram Upload', 'use_ocr': 'true'}
            
            response = await client.post(
                f"{API_URL}/upload",
                files=files,
                data=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                task_id = response.json().get("task_id")
                await update.message.reply_text(
                    f"✅ Arquivo enviado! ID da tarefa: `{task_id}`\n"
                    "O processamento ocorre em background. Em breve as informações estarão disponíveis para consulta.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Falha ao enviar arquivo para o servidor.")
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        await update.message.reply_text("⚠️ Erro ao processar o arquivo. Verifique a conexão com o servidor.")

if __name__ == '__main__':
    if not TOKEN:
        print("Erro: TELEGRAM_BOT_TOKEN não definido no .env")
        exit(1)
        
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stats', get_stats))
    application.add_handler(CommandHandler('clear', clear_db))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    
    print("🤖 Hermes Telegram Bot está ativo e aguardando mensagens...")
    application.run_polling()
