import os
import sys
from pathlib import Path
from fpdf import FPDF

# Adiciona o diretório atual ao path para importar o Hermes
sys.path.append(str(Path(__file__).parent))

from src.services import HermesService
from src.config import RAGConfig

def create_mock_pdfs(output_dir: Path):
    output_dir.mkdir(exist_ok=True)
    
    # 1. Contrato de Prestação de Serviços
    pdf1 = FPDF()
    pdf1.add_page()
    pdf1.set_font("helvetica", "B", 16)
    pdf1.cell(0, 10, "CONTRATO DE PRESTAÇÃO DE SERVIÇOS ADVOCATÍCIOS", ln=True, align="C")
    pdf1.ln(10)
    pdf1.set_font("helvetica", "", 12)
    content1 = [
        "CONTRATANTE: Empresa Global S.A., inscrita no CNPJ sob o nº 00.111.222/0001-33.",
        "CONTRATADO: Escritório Silva & Associados, inscrito na OAB/SP sob o nº 12.345.",
        "",
        "CLÁUSULA PRIMEIRA - DO OBJETO",
        "O presente contrato tem como objeto a assessoria jurídica mensal em demandas cíveis e trabalhistas.",
        "",
        "CLÁUSULA SEGUNDA - DOS HONORÁRIOS",
        "A CONTRATANTE pagará ao CONTRATADO o valor mensal de R$ 5.000,00 (cinco mil reais).",
        "Em caso de êxito em ações judiciais, será devido o percentual de 10% sobre o proveito econômico.",
        "",
        "CLÁUSULA TERCEIRA - DO FORO",
        "As partes elegem o foro da Comarca de São Paulo/SP para dirimir quaisquer dúvidas deste contrato.",
        "",
        "Data: 10 de Janeiro de 2026."
    ]
    content1_text = "\n".join(content1)
    pdf1.multi_cell(0, 10, content1_text)
    pdf1.output(str(output_dir / "contrato_global_sa.pdf"))

    # 2. Petição Inicial
    pdf2 = FPDF()
    pdf2.add_page()
    pdf2.set_font("helvetica", "B", 14)
    pdf2.cell(0, 10, "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA 1ª VARA CÍVEL", ln=True, align="L")
    pdf2.cell(0, 10, "DA COMARCA DE SÃO PAULO - SP", ln=True, align="L")
    pdf2.ln(5)
    pdf2.set_font("helvetica", "", 12)
    pdf2.cell(0, 10, "Processo nº 1234567-89.2024.8.26.0001", ln=True, align="R")
    pdf2.ln(10)
    content2 = [
        "JOÃO DA SILVA, brasileiro, casado, portador do CPF nº 111.222.333-44, residente em São Paulo/SP,",
        "vem, por intermédio de seu advogado, propor a presente:",
        "",
        "AÇÃO DE INDENIZAÇÃO POR DANOS MORAIS",
        "",
        "em face de BANCO X S.A., pelos fatos a seguir expostos:",
        "O Autor teve seu nome indevidamente inscrito nos órgãos de proteção ao crédito por uma dívida já quitada.",
        "Tal fato causou graves transtornos, impedindo a obtenção de crédito imobiliário.",
        "",
        "DOS PEDIDOS:",
        "1. A condenação do Réu ao pagamento de R$ 15.000,00 a título de danos morais.",
        "2. A imediata exclusão do nome do Autor dos cadastros de inadimplentes.",
        "",
        "Termos em que pede deferimento."
    ]
    content2_text = "\n".join(content2)
    pdf2.multi_cell(0, 10, content2_text)
    pdf2.output(str(output_dir / "peticao_joao_silva.pdf"))

    # 3. Guia do Escritório
    pdf3 = FPDF()
    pdf3.add_page()
    pdf3.set_font("helvetica", "B", 16)
    pdf3.cell(0, 10, "GUIA DE PROCEDIMENTOS INTERNOS - SILVA & ASSOCIADOS", ln=True, align="C")
    pdf3.ln(10)
    pdf3.set_font("helvetica", "", 12)
    content3 = [
        "1. HORÁRIO DE FUNCIONAMENTO",
        "O escritório funciona de segunda a sexta, das 09:00 às 18:00.",
        "",
        "2. ATENDIMENTO AO CLIENTE",
        "Dúvidas básicas devem ser preferencialmente respondidas via Hermes RAG.",
        "Consultas presenciais devem ser agendadas com 48h de antecedência.",
        "",
        "3. USO DE INTELIGÊNCIA ARTIFICIAL",
        "O uso do Hermes RAG é obrigatório para a revisão inicial de contratos e busca de teses em petições antigas.",
        "Sempre verifique a citação da página antes de incluir a informação em uma petição oficial.",
        "",
        "4. SEGURANÇA DOS DADOS",
        "Não compartilhe senhas do sistema e mantenha os documentos sempre na pasta oficial para indexação."
    ]
    content3_text = "\n".join(content3)
    pdf3.multi_cell(0, 10, content3_text)
    pdf3.output(str(output_dir / "guia_interno_escritorio.pdf"))
    
    print(f"Mock PDFs criados em {output_dir}")

def index_mock_data(data_dir: Path):
    print("Iniciando indexação dos documentos de demonstração...")
    config = RAGConfig()
    service = HermesService(config)
    
    # Prepara os arquivos para o serviço
    files_data = []
    for pdf_file in data_dir.glob("*.pdf"):
        with open(pdf_file, "rb") as f:
            files_data.append({
                "name": pdf_file.name,
                "content": f.read()
            })
    
    if not files_data:
        print("Nenhum PDF encontrado para indexar.")
        return

    # Limpa a base anterior para o demo ficar limpo (opcional, mas recomendado para demo)
    print("Limpando base de dados existente para o demo...")
    service.clear_database()

    # Indexa os arquivos
    # Usamos o subject 'Demo Jurídico'
    result = service.process_and_index_files(files_data, subject="Demo Jurídico", use_ocr=False)
    
    if result["success"]:
        print(f"Sucesso! {result['count']} documentos indexados.")
    else:
        print(f"Falha na indexação: {result.get('message')}")

if __name__ == "__main__":
    demo_dir = Path("./demo_data")
    create_mock_pdfs(demo_dir)
    
    # Verifica se a API Key está configurada antes de indexar
    config = RAGConfig()
    if not config.llm_api_key:
        print("\nAVISO: LLM_API_KEY não configurada no .env.")
        print("Os PDFs foram criados, mas a indexação foi pulada.")
        print("Configure sua chave no arquivo .env e rode o script novamente.")
    else:
        index_mock_data(demo_dir)
