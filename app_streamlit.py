# app_streamlit.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from processador import process_file # Importa a função do nosso arquivo unificado

# --- Configuração da Página ---
st.set_page_config(page_title="Processador de Escalas", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Processador de Escalas de Trabalho")

# --- Lógica do Sidebar para Upload ---
st.sidebar.header("⚙️ Configurações")
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo .csv ou .xlsx", type=["csv", "xlsx"])

# Inicializa o session_state para guardar o caminho do resultado
if 'output_path' not in st.session_state:
    st.session_state.output_path = None
if 'processed_df_head' not in st.session_state:
    st.session_state.processed_df_head = None
    
# Botão de processamento
process_button = st.sidebar.button("🚀 Processar Escalas", disabled=(not uploaded_file))

# --- Lógica de Processamento ---
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

if process_button:
    try:
        # Mostra um spinner durante o processamento
        with st.spinner('Aguarde... Lendo e processando o arquivo.'):
            df = None
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            
            # Armazena o cabeçalho do DF no estado da sessão para exibição
            st.session_state.processed_df_head = df.head(10)

            # Define um caminho único para o arquivo de saída
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"resultado_{timestamp}.json"
            output_path = os.path.join(output_dir, output_filename)
            
            # Processa o arquivo e salva o resultado
            process_file(df, output_path)
            
            # Armazena o caminho do arquivo no estado da sessão
            st.session_state.output_path = output_path
            
        st.success("✅ Processamento concluído com sucesso!")

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
        st.session_state.output_path = None # Limpa em caso de erro

# --- Exibição dos Resultados ---
if st.session_state.processed_df_head is not None:
    st.subheader("📄 Pré-visualização do Arquivo Processado")
    st.dataframe(st.session_state.processed_df_head)

if st.session_state.output_path:
    st.subheader("⬇️ Download do Resultado")
    output_path = st.session_state.output_path
    
    with open(output_path, "rb") as f:
        # Extrai apenas o nome do arquivo para o download
        file_name_for_download = os.path.basename(output_path)
        st.download_button(
            label=f"📥 Baixar {file_name_for_download}",
            data=f,
            file_name=file_name_for_download,
            mime="application/json"
        )
    
    with st.expander("Visualizar JSON gerado"):
        with open(output_path, "r", encoding="utf-8") as f:
            st.json(f.read())

# Mensagem inicial se nenhum arquivo for carregado
if not uploaded_file:
    st.info("Por favor, carregue um arquivo CSV ou XLSX na barra lateral para começar.")