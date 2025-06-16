# app.py (Versão Final Corrigida)

import streamlit as st
import sqlite3
import json
import plotly.express as px
import pandas as pd
from rapidfuzz import fuzz
import copy
import sys
import os
import streamlit.components.v1 as components
from datetime import datetime

# =====================================================================================
# CONFIGURAÇÃO INICIAL (DEVE SER A PRIMEIRA PARTE DO SCRIPT)
# =====================================================================================

# --- Configuração da Página (Chamada única e no topo) ---
st.set_page_config(page_title="Central de ADM Pessoal", layout="wide")

# --- Conexão com o Banco de Dados ---
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS jsons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, data TEXT)''')
conn.commit()

# --- Importação segura do processador ---
try:
    from processador import process_file
except ImportError:
    st.error("Erro Crítico: O arquivo 'processador.py' não foi encontrado. Ele deve estar na mesma pasta que o app.py.")
    st.stop()


# =====================================================================================
# FUNÇÕES DE CADA PÁGINA (Renderizam apenas o conteúdo principal)
# =====================================================================================

def pagina_documentacao():
    st.header("📄 Documentação Recursos")
    st.write("Este é o relatório técnico gerado pelo PyInstaller, mostrando as dependências e módulos importados pela aplicação.")
    html_file_path = 'gestao de escalas.html'
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        with st.container(border=True):
            components.html(source_code, height=600, scrolling=True)
    except FileNotFoundError:
        st.error(f"Erro: O arquivo {html_file_path} não foi encontrado.")

def pagina_importar_escala(uploaded_json):
    st.header("📥 Importar Escala")
    if uploaded_json:
        try:
            json_data = json.load(uploaded_json)
            # Insere no banco de dados
            cursor.execute("INSERT INTO jsons (name, data) VALUES (?, ?)", (uploaded_json.name, json.dumps(json_data)))
            conn.commit()
            st.success(f"Arquivo '{uploaded_json.name}' importado com sucesso!")
        except json.JSONDecodeError:
            st.error("Erro: O arquivo fornecido não é um JSON válido.")
        except Exception as e:
            st.error(f"Ocorreu um erro ao importar o arquivo: {e}")

def pagina_exportar_json_personalizado(selected_file, selected_scales_keys):
    st.header("🧩 Exportar JSON Personalizado")
    if selected_file and selected_scales_keys:
        try:
            cursor.execute("SELECT data FROM jsons WHERE name = ?", (selected_file,))
            result = cursor.fetchone()
            if result:
                full_json = json.loads(result[0])
                
                # Filtra as escalas selecionadas
                filtered_scales = [scale for scale in full_json.get("escalas", []) if scale.get("key") in selected_scales_keys]
                
                # Coleta as jornadas usadas por essas escalas
                used_jornada_keys = {j_key for scale in filtered_scales for j_key in scale.get("JORNADAS", [])}
                
                # Filtra as jornadas
                filtered_jornadas = {key: jornada for key, jornada in full_json.get("jornadas", {}).items() if key in used_jornada_keys}
                
                # Monta o novo JSON
                new_json_data = {
                    "escalas": filtered_scales,
                    "jornadas": filtered_jornadas,
                    "horas_adicionais": full_json.get("horas_adicionais", [])
                }
                
                new_json_str = json.dumps(new_json_data, indent=4, ensure_ascii=False)
                
                st.success("JSON personalizado gerado com sucesso!")
                st.download_button(
                    label="📥 Baixar JSON Personalizado",
                    data=new_json_str,
                    file_name=f"personalizado_{selected_file}",
                    mime="application/json"
                )
                with st.expander("Visualizar JSON Gerado"):
                    st.json(new_json_data)
        except Exception as e:
            st.error(f"Ocorreu um erro ao gerar o JSON personalizado: {e}")

def pagina_duplicar_para_coligadas(selected_file, prefixo, sufixo, coligada_filial, tipo_duplicacao):
    st.header("🔎 Duplicar para Coligadas/Filiais")
    if st.button("Executar Duplicação") and selected_file:
        try:
            cursor.execute("SELECT data FROM jsons WHERE name = ?", (selected_file,))
            result = cursor.fetchone()
            if result:
                original_json = json.loads(result[0])
                new_json = copy.deepcopy(original_json) # Cria uma cópia profunda para não alterar o original

                for escala in new_json.get("escalas", []):
                    if tipo_duplicacao == "Prefixo":
                        escala["NOME"] = f"{prefixo}{escala.get('NOME', '')}"
                    elif tipo_duplicacao == "Sufixo":
                        escala["NOME"] = f"{escala.get('NOME', '')}{sufixo}"
                    
                    # Adiciona a lógica de coligada/filial se necessário
                    # Exemplo: escala['COD_COLIGADA'] = coligada_filial

                new_name = f"duplicado_{coligada_filial}_{selected_file}"
                cursor.execute("INSERT INTO jsons (name, data) VALUES (?, ?)", (new_name, json.dumps(new_json)))
                conn.commit()
                st.success(f"Arquivo duplicado e salvo como '{new_name}' com sucesso!")
        except Exception as e:
            st.error(f"Ocorreu um erro durante a duplicação: {e}")

def pagina_processador_de_escalas_via_csv(uploaded_file, process_button):
    st.header("📊 Gerar Escalas Através de CSV")
    st.info("Carregue um arquivo CSV ou XLSX na barra lateral para convertê-lo em um arquivo JSON estruturado.")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    if process_button and uploaded_file:
        try:
            with st.spinner('Aguarde... Lendo e processando o arquivo.'):
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)
                st.session_state.processed_df_head = df.head(10)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"resultado_{timestamp}.json"
                output_path = os.path.join(output_dir, output_filename)
                process_file(df, output_path)
                st.session_state.output_path = output_path
            st.success("✅ Processamento concluído com sucesso!")
        except Exception as e:
            st.error(f"❌ Erro ao processar o arquivo: {e}")
            st.session_state.output_path = None

    if st.session_state.get('processed_df_head') is not None:
        st.subheader("📄 Pré-visualização do Arquivo de Entrada")
        st.dataframe(st.session_state.processed_df_head)
    if st.session_state.get('output_path'):
        st.subheader("⬇️ Download do Resultado")
        output_path = st.session_state.output_path
        try:
            with open(output_path, "rb") as f:
                file_name_for_download = os.path.basename(output_path)
                st.download_button(label=f"📥 Baixar {file_name_for_download}", data=f, file_name=file_name_for_download, mime="application/json")
            with st.expander("Visualizar JSON gerado"):
                with open(output_path, "r", encoding="utf-8") as f:
                    st.json(f.read())
        except FileNotFoundError:
            st.error("O arquivo de resultado não foi encontrado.")

def pagina_excluir_arquivo(file_to_delete):
    st.header("🗑️ Excluir Arquivo")
    if file_to_delete:
        if st.button(f"Confirmar Exclusão de '{file_to_delete}'", type="primary"):
            try:
                cursor.execute("DELETE FROM jsons WHERE name = ?", (file_to_delete,))
                conn.commit()
                st.success(f"Arquivo '{file_to_delete}' excluído com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir o arquivo: {e}")

def pagina_exportar_lista():
    st.header("📁 Exportar Lista de Arquivos e Escalas")
    dados = []
    try:
        cursor.execute("SELECT name, data FROM jsons")
        all_files = cursor.fetchall()
        for name, data in all_files:
            json_data = json.loads(data)
            for escala in json_data.get("escalas", []):
                dados.append([name, escala.get("NOME", "Nome não encontrado")])
        if dados:
            df = pd.DataFrame(dados, columns=["Arquivo", "Escala"])
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(label="📥 Baixar CSV", data=csv, file_name="lista_arquivos_escalas.csv", mime="text/csv")
        else:
            st.info("Nenhuma escala encontrada no banco de dados.")
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")

# =====================================================================================
# LÓGICA PRINCIPAL DA APLICAÇÃO (MENU E ROTEAMENTO)
# =====================================================================================

# --- Menu Principal na Sidebar ---
st.sidebar.title("⚙️ Menu")
menu_options = [
    "📄 Documentação Recursos",
    "📥 Importar Escala",
    "🧩 Exportar JSON Personalizado",
    "🔎 Duplicar para coligadas/filiais",
    "📊 Gerar escalas através de CSV",
    "🗑️ Excluir Arquivo",
    "📁 Exportar Lista de Arquivos e Escalas"
]
menu = st.sidebar.radio("Escolha uma opção:", menu_options)

# --- Roteamento e Renderização Condicional da Sidebar ---
if menu == "📄 Documentação Recursos":
    pagina_documentacao()

elif menu == "📥 Importar Escala":
    st.sidebar.header("Opções de Importação")
    uploaded_json = st.sidebar.file_uploader("Selecione o arquivo JSON", type=["json"])
    pagina_importar_escala(uploaded_json)

elif menu == "🧩 Exportar JSON Personalizado":
    st.sidebar.header("Opções de Exportação")
    cursor.execute("SELECT name FROM jsons")
    files = [row[0] for row in cursor.fetchall()]
    selected_file = st.sidebar.selectbox("Selecione um arquivo de origem:", files)
    
    selected_scales_keys = []
    if selected_file:
        cursor.execute("SELECT data FROM jsons WHERE name = ?", (selected_file,))
        result = cursor.fetchone()
        if result:
            json_data = json.loads(result[0])
            scale_options = {scale.get("key"): scale.get("NOME") for scale in json_data.get("escalas", [])}
            selected_scales_keys = st.sidebar.multiselect("Selecione as escalas para exportar:", options=scale_options.keys(), format_func=lambda k: scale_options[k])
    
    pagina_exportar_json_personalizado(selected_file, selected_scales_keys)

elif menu == "🔎 Duplicar para coligadas/filiais":
    st.sidebar.header("Opções de Duplicação")
    cursor.execute("SELECT name FROM jsons")
    files = [row[0] for row in cursor.fetchall()]
    selected_file = st.sidebar.selectbox("Selecione o arquivo para duplicar:", files, key="dup_select")
    tipo_duplicacao = st.sidebar.selectbox("Tipo de alteração no nome:", ["Prefixo", "Sufixo"])
    prefixo = ""
    sufixo = ""
    if tipo_duplicacao == "Prefixo":
        prefixo = st.sidebar.text_input("Prefixo:")
    else:
        sufixo = st.sidebar.text_input("Sufixo:")
    coligada_filial = st.sidebar.text_input("Código da Coligada/Filial:")
    
    pagina_duplicar_para_coligadas(selected_file, prefixo, sufixo, coligada_filial, tipo_duplicacao)

elif menu == "📊 Gerar escalas através de CSV":
    st.sidebar.header("Opções do Processador")
    uploaded_file = st.sidebar.file_uploader("Selecione o arquivo .csv ou .xlsx", type=["csv", "xlsx"], key="escala_uploader")
    process_button = st.sidebar.button("🚀 Processar Escalas", disabled=(not uploaded_file))
    
    pagina_processador_de_escalas_via_csv(uploaded_file, process_button)

elif menu == "🗑️ Excluir Arquivo":
    st.sidebar.header("Opções de Exclusão")
    cursor.execute("SELECT name FROM jsons")
    files_to_delete = [row[0] for row in cursor.fetchall()]
    file_to_delete = st.sidebar.selectbox("Selecione o arquivo para excluir:", files_to_delete, index=None, placeholder="Selecione um arquivo...")
    
    pagina_excluir_arquivo(file_to_delete)

elif menu == "📁 Exportar Lista de Arquivos e Escalas":
    pagina_exportar_lista()

