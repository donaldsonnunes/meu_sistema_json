# app.py (Versão Final Corrigida e Estruturada)

import streamlit as st
import sqlite3
import json
import pandas as pd
from rapidfuzz import fuzz
import copy
import os
import streamlit.components.v1 as components
from datetime import datetime
from datetime import time
import uuid

# =====================================================================================
# CONFIGURAÇÃO INICIAL E CONEXÃO COM BANCO DE DADOS
# =====================================================================================

# --- Configuração da Página (Deve ser o primeiro comando Streamlit) ---
st.set_page_config(page_title="Central de ADM Pessoal", layout="wide")

# --- Conexão com o Banco de Dados ---
@st.cache_resource
def get_db_connection():
    """Cria e gerencia a conexão com o banco de dados."""
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.isolation_level = None
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jsons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, data TEXT)''')
    conn.commit()
    return conn

conn = get_db_connection()

# --- Importação segura do processador ---
try:
    from processador import process_file
except ImportError:
    st.error("Erro Crítico: O arquivo 'processador.py' não foi encontrado. Ele deve estar na mesma pasta que o app.py.")
    st.stop()


# =====================================================================================
# FUNÇÕES AUXILIARES
# =====================================================================================

def salvar_no_banco(conexao, dados_json, nome=None, selected_id=None):
    """Salva ou atualiza um registro no banco de dados."""
    cursor = conexao.cursor()
    json_str = json.dumps(dados_json, indent=4, ensure_ascii=False)
    try:
        if selected_id:
            cursor.execute("UPDATE jsons SET data = ?, name = ? WHERE id = ?", (json_str, nome, selected_id))
        elif nome:
            cursor.execute("SELECT id FROM jsons WHERE name = ?", (nome,))
            if cursor.fetchone():
                st.warning(f"Um arquivo com o nome '{nome}' já existe. A operação foi cancelada para evitar duplicatas.")
                return False
            cursor.execute("INSERT INTO jsons (name, data) VALUES (?, ?)", (nome, json_str))
        conexao.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        return False

# =====================================================================================
# DEFINIÇÃO DE CADA PÁGINA DA APLICAÇÃO
# =====================================================================================

# Substitua a função de documentação existente em app.py por esta

def pagina_documentacao():
    st.header("📄 Documentação da Gestão de Escalas")
    st.markdown("Bem-vindo! Esta ferramenta foi desenvolvida para processar, gerenciar e otimizar escalas de trabalho de forma inteligente. Abaixo estão descritos os recursos disponíveis no menu lateral.")
    
    st.divider()
    # =======================================================================
    st.subheader("Visão Geral e Gestão")
    # =======================================================================

    with st.container(border=True):
        st.markdown("##### 📊 Dashboard")
        st.write("""
        **O que faz:** É a página inicial da aplicação. Oferece um resumo quantitativo dos seus dados, mostrando o total de arquivos, escalas e jornadas no sistema. Também exibe uma lista de todos os arquivos salvos para acesso rápido.
        """)

    with st.container(border=True):
        st.markdown("##### 📥 Importar Escala")
        st.write("""
        **O que faz:** Permite carregar um arquivo de escalas no formato `.json` (gerado externamente ou por esta própria ferramenta) e salvá-lo no banco de dados interno da aplicação.
        
        **Como usar:**
        1. Clique no botão **"Procurar arquivos"**.
        2. Selecione um arquivo `.json` do seu computador.
        3. Clique no botão **"Importar Arquivo Agora"**.
        """)
    
    with st.container(border=True):
        st.markdown("##### 🧩 Exportar JSON Personalizado")
        st.write("""
        **O que faz:** Permite selecionar um arquivo JSON do banco de dados e escolher escalas específicas dentro dele para gerar um novo arquivo `.json` contendo apenas os dados selecionados.
        
        **Como usar:**
        1. Selecione um **Arquivo de origem** na lista.
        2. Na caixa **"Selecione as escalas"**, clique para ver a lista e marque uma ou mais escalas que deseja exportar.
        3. Clique em **"Gerar e Baixar JSON"** para que o botão de download apareça.
        """)

    with st.container(border=True):
        st.markdown("##### 📁 Exportar Lista de Arquivos e Escalas")
        st.write("""
        **O que faz:** Gera uma tabela com duas colunas ("Arquivo" e "Escala"), listando todas as escalas contidas em todos os arquivos do banco de dados. Permite baixar esta lista como um arquivo `.csv`.
        """)
        
    with st.container(border=True):
        st.markdown("##### 🗑️ Excluir Arquivo")
        st.write("""
        **O que faz:** Remove permanentemente um arquivo JSON do banco de dados da aplicação.
        
        **Como usar:**
        1. Selecione o arquivo que deseja remover na caixa de seleção.
        2. Leia o aviso de confirmação e clique no botão **"Confirmar Exclusão"**.
        """)

    st.divider()
    # =======================================================================
    st.subheader("Criação e Processamento")
    # =======================================================================

    with st.container(border=True):
        st.markdown("##### 📊 Gerar escalas através de CSV")
        st.write("""
        **O que faz:** O recurso principal da aplicação. Converte um arquivo `.csv` ou `.xlsx` com descrições textuais de escalas em um arquivo JSON totalmente estruturado e otimizado.
        
        **Funcionalidades Inteligentes:**
        - **Unificação Automática:** Identifica escalas que são funcionalmente idênticas (mesmos horários e dias), mesmo que escritas de forma diferente, e as unifica para evitar duplicatas.
        - **Geração de Log:** Ao final do processamento, se alguma escala foi unificada, um botão aparecerá para baixar um arquivo `.txt` com o **"Log de Unificações"**, detalhando exatamente quais escalas foram agrupadas.
        """)

    st.divider()
    # =======================================================================
    st.subheader("Edição e Manutenção")
    # =======================================================================

    with st.container(border=True):
        st.markdown("##### ✏️ Editor Visual")
        st.write("""
        **O que faz:** Permite editar os detalhes de uma **escala individual** de forma visual e intuitiva.
        
        **Como usar:**
        1.  **Passo 1:** Selecione o arquivo JSON que contém a escala.
        2.  **Passo 2:** Selecione a escala específica que deseja modificar.
        3.  Um formulário aparecerá, permitindo alterar o Nome, Código, e o mais importante: **trocar a jornada de cada dia da semana** usando um menu de seleção.
        4.  Clique em "Salvar Alterações" para atualizar a escala.
        """)
        
    with st.container(border=True):
        st.markdown("##### 📕 Editor de Jornadas")
        st.write("""
        **O que faz:** Permite gerenciar as "peças" que compõem as escalas: as jornadas de trabalho.
        
        **Como usar:**
        1.  Selecione uma jornada da lista (ex: "08:00 AS 18:00").
        2.  Um formulário de edição permitirá alterar o nome da jornada e os **horários exatos** de entrada, saída e intervalo.
        3.  Ao salvar, o sistema **atualiza esta jornada em todos os arquivos e escalas que a utilizam**, garantindo consistência total.
        """)

    with st.container(border=True):
        st.markdown("##### 📝 Edição em Lote / Duplicar para coligadas")
        st.write("""
        **O que faz:** Ferramentas para criar novas escalas em lote, buscando por um texto específico (prefixo) em uma tag e o substituindo por um novo valor. Ideal para criar cópias de um conjunto de escalas para uma nova filial ou centro de custo.
        """)

def pagina_dashboard():
    st.header("📊 Dashboard de Controle")
    st.markdown("Visão geral dos dados e atividade no sistema.")

    try:
        cursor = conn.cursor()
        
        # 1. Obter o número total de arquivos
        cursor.execute("SELECT COUNT(*) FROM jsons")
        total_arquivos = cursor.fetchone()[0]

        # 2. Calcular o total de escalas e jornadas
        cursor.execute("SELECT data FROM jsons")
        rows = cursor.fetchall()
        
        total_escalas = 0
        total_jornadas = 0
        
        arquivos_info = []

        for row in rows:
            try:
                # Carrega o JSON de cada arquivo
                json_data = json.loads(row[0])
                num_escalas = len(json_data.get("escalas", []))
                num_jornadas = len(json_data.get("jornadas", {}))
                
                total_escalas += num_escalas
                total_jornadas += num_jornadas
                
                # Coleta info para a tabela de arquivos (se houver nome no DB)
                # Vamos precisar buscar o nome do arquivo também
            except (json.JSONDecodeError, TypeError):
                continue # Ignora registros que não são JSON válidos

        # Exibir as métricas em colunas
        col1, col2, col3 = st.columns(3)
        col1.metric("Arquivos Salvos", f"{total_arquivos} arquivos")
        col2.metric("Total de Escalas", f"{total_escalas} escalas")
        col3.metric("Total de Jornadas", f"{total_jornadas} jornadas")

        st.divider()

        # Exibir uma lista dos arquivos no banco de dados
        st.subheader("📁 Arquivos no Banco de Dados")
        cursor.execute("SELECT id, name, data FROM jsons ORDER BY name")
        files_data = cursor.fetchall()

        if not files_data:
            st.info("Nenhum arquivo encontrado no banco de dados. Comece importando uma escala.")
        else:
            display_data = []
            for id_file, name, json_str in files_data:
                try:
                    json_data = json.loads(json_str)
                    num_escalas = len(json_data.get("escalas", []))
                    display_data.append({"ID": id_file, "Nome do Arquivo": name, "Nº de Escalas": num_escalas})
                except (json.JSONDecodeError, TypeError):
                    display_data.append({"ID": id_file, "Nome do Arquivo": name, "Nº de Escalas": "Erro de Leitura"})
            
            df = pd.DataFrame(display_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar o dashboard: {e}")

def pagina_importar_escala():
    st.header("📥 Importar Escala")
    uploaded_json = st.file_uploader("Selecione o arquivo JSON para importar", type=["json"], key="import_uploader")
    if uploaded_json:
        if st.button("Importar Arquivo Agora", use_container_width=True, type="primary"):
            try:
                uploaded_json.seek(0)
                json_data = json.load(uploaded_json)
                if salvar_no_banco(conn, json_data, nome=uploaded_json.name):
                    st.success(f"Arquivo '{uploaded_json.name}' importado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
            except json.JSONDecodeError:
                st.error("Erro: O arquivo fornecido não é um JSON válido.")
            except Exception as e:
                st.error(f"Ocorreu um erro ao importar o arquivo: {e}")

def pagina_edicao_em_lote():
    st.header("📝 Edição em Lote")
    st.info("Esta ferramenta cria novas escalas em lote com base na substituição de prefixo em uma tag específica.")
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM jsons ORDER BY name")
    rows = cursor.fetchall()

    if not rows:
        st.warning("Nenhum arquivo no banco de dados. Importe um arquivo primeiro.")
        return

    with st.container(border=True):
        st.markdown("#### 📄 Passo 1: Selecione o Alvo")
        options_list = [f"{r[0]} - {r[1]}" for r in rows]
        json_id_str = st.selectbox("Selecione o JSON para editar", options_list, key="lote_json_select", index=None, placeholder="Escolha um arquivo...")
    
    if json_id_str:
        selected_id = int(json_id_str.split(" - ")[0])
        selected_name = " - ".join(json_id_str.split(" - ")[1:])
        
        cursor.execute("SELECT data FROM jsons WHERE id=?", (selected_id,))
        result = cursor.fetchone()
        if not result:
            st.error("Arquivo não encontrado no banco de dados."); return

        original_data = json.loads(result[0])
        escalas = original_data.get('escalas', [])

        if not escalas:
            st.warning("O arquivo selecionado não contém 'escalas'.")
        else:
            todas_tags = sorted(list(set(key for esc in escalas for key in esc.keys())))
            with st.container(border=True):
                st.markdown("#### 🏷️ Passo 2: Defina a Regra")
                tag_selecionada = st.selectbox("Selecione a Tag para a busca", todas_tags, key="lote_tag_select")
                col1, col2 = st.columns(2)
                with col1: valor_localizar = st.text_input("Texto a ser localizado (prefixo)", key="lote_search")
                with col2: valor_substituir = st.text_input("Substituir o prefixo por", key="lote_replace")

            if st.button("👁️ Pré-visualizar alterações", use_container_width=True):
                dados_preview, novas_escalas = [], []
                if valor_localizar:
                    for esc in original_data.get("escalas", []):
                        valor_original_tag = esc.get(tag_selecionada)
                        if isinstance(valor_original_tag, str) and valor_original_tag.startswith(valor_localizar):
                            nova_escala = copy.deepcopy(esc)
                            valor_antigo_tag = nova_escala[tag_selecionada]
                            novo_valor_tag = valor_substituir + valor_antigo_tag[len(valor_localizar):]
                            nova_escala[tag_selecionada] = novo_valor_tag
                            nome_antigo_escala = nova_escala.get("NOME", "")
                            novo_nome_escala = f"{nome_antigo_escala} - {valor_substituir}"
                            nova_escala["NOME"] = novo_nome_escala
                            nova_escala["key"] = uuid.uuid4().hex
                            novas_escalas.append(nova_escala)
                            dados_preview.append({"Nome Original": nome_antigo_escala, "Novo Nome Proposto": novo_nome_escala, f"Valor Original ({tag_selecionada})": valor_antigo_tag, f"Valor Proposto ({tag_selecionada})": novo_valor_tag})
                
                if dados_preview:
                    json_modificado = copy.deepcopy(original_data)
                    json_modificado["escalas"].extend(novas_escalas)
                    st.session_state.update({'dados_preview': dados_preview, 'json_modificado': json_modificado,'novas_escalas': novas_escalas, 'selected_id_lote': selected_id,'selected_name_lote': selected_name})
                else:
                    st.warning("Nenhum registro encontrado com o critério especificado.")
                    if 'dados_preview' in st.session_state: del st.session_state['dados_preview']
            
            if st.session_state.get('dados_preview'):
                with st.container(border=True):
                    st.markdown("#### 📊 Passo 3: Confirme e Salve as Alterações")
                    st.success(f"Foram encontradas {len(st.session_state['dados_preview'])} escalas. Serão **criados {len(st.session_state['dados_preview'])} novos registros** de escala.")
                    st.dataframe(pd.DataFrame(st.session_state['dados_preview']), use_container_width=True)
                    st.divider()
                    col_salvar1, col_salvar2 = st.columns(2)
                    with col_salvar1:
                        st.markdown("##### 💾 Opção 1: Salvar Tudo")
                        st.write("Adiciona as novas escalas ao arquivo original e salva o resultado.")
                        opcao = st.radio("Como deseja salvar?", ["Sobrescrever arquivo existente", "Salvar como novo arquivo"], key="lote_save_option", horizontal=True)
                        novo_nome_tudo = ""
                        if opcao == "Salvar como novo arquivo": novo_nome_tudo = st.text_input("Nome do novo arquivo:", value=st.session_state.get('selected_name_lote', 'arquivo.json').replace(".json", "_modificado.json"), key="lote_new_name_all")
                        if st.button("Salvar Tudo Agora", key="lote_save_btn_all", use_container_width=True, type="primary"):
                            json_final = st.session_state['json_modificado']
                            if opcao == "Sobrescrever arquivo existente":
                                salvar_no_banco(conn, json_final, nome=st.session_state['selected_name_lote'], selected_id=st.session_state['selected_id_lote'])
                                st.success("✅ Alterações salvas no arquivo original.")
                            elif not novo_nome_tudo.strip(): st.error("❌ Informe um nome para o novo arquivo.")
                            else:
                                if salvar_no_banco(conn, json_final, nome=novo_nome_tudo.strip()):
                                    st.success(f"✅ Novo arquivo '{novo_nome_tudo}' salvo com sucesso!")
                            st.rerun()
                    with col_salvar2:
                        st.markdown("##### 💾 Opção 2: Salvar Somente Novas")
                        st.write("Cria um novo arquivo contendo apenas as escalas geradas.")
                        novo_nome_novas = st.text_input("Nome do novo arquivo:", value=st.session_state.get('selected_name_lote', 'arquivo.json').replace(".json", "_apenas_novas.json"), key="lote_new_name_only")
                        if st.button("Salvar Somente Novas", key="lote_save_btn_only", use_container_width=True):
                            if not novo_nome_novas.strip(): st.error("❌ Informe um nome para o novo arquivo.")
                            else:
                                with st.spinner("Preparando novo arquivo..."):
                                    escalas_novas = st.session_state['novas_escalas']
                                    jornadas_originais = st.session_state['json_modificado'].get('jornadas', {})
                                    horas_originais = st.session_state['json_modificado'].get('horas_adicionais', [])
                                    ids_jornadas_necessarias = set(j_key for esc in escalas_novas for j_key in esc.get('JORNADAS', []))
                                    jornadas_filtradas = {k: v for k, v in jornadas_originais.items() if k in ids_jornadas_necessarias}
                                    json_apenas_novas = {"escalas": escalas_novas, "jornadas": jornadas_filtradas, "horas_adicionais": horas_originais}
                                    if salvar_no_banco(conn, json_apenas_novas, nome=novo_nome_novas.strip()):
                                        st.success(f"✅ Novo arquivo '{novo_nome_novas}' salvo!")
                                st.rerun()

def pagina_exportar_json_personalizado():
    st.header("🧩 Exportar JSON Personalizado")
    
    with st.container(border=True):
        st.markdown("#### Opções de Exportação")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM jsons ORDER BY name")
        files = [row[0] for row in cursor.fetchall()]
        if not files:
            st.warning("Nenhum arquivo JSON disponível para exportação."); return
            
        selected_file = st.selectbox("Arquivo de origem:", files, key="export_select")
        selected_scales_keys = []
        if selected_file:
            cursor.execute("SELECT data FROM jsons WHERE name = ?", (selected_file,))
            result = cursor.fetchone()
            if result:
                json_data = json.loads(result[0])
                scale_options = {scale.get("key"): scale.get("NOME") for scale in json_data.get("escalas", [])}
                selected_scales_keys = st.multiselect("Selecione as escalas:", options=list(scale_options.keys()), format_func=lambda k: scale_options.get(k, k))

    if selected_file and selected_scales_keys:
        if st.button("Gerar e Baixar JSON", use_container_width=True, type="primary"):
            used_jornada_keys = {j_key for scale in json_data.get("escalas", []) if scale.get("key") in selected_scales_keys for j_key in scale.get("JORNADAS", [])}
            filtered_jornadas = {key: jornada for key, jornada in json_data.get("jornadas", {}).items() if key in used_jornada_keys}
            new_json_data = {
                "escalas": [s for s in json_data.get("escalas", []) if s.get("key") in selected_scales_keys],
                "jornadas": filtered_jornadas,
                "horas_adicionais": json_data.get("horas_adicionais", [])
            }
            st.session_state.export_data = json.dumps(new_json_data, indent=4, ensure_ascii=False)
            st.session_state.export_filename = f"personalizado_{selected_file}"
            st.success("JSON personalizado pronto para download!")
    
    if 'export_data' in st.session_state:
        st.download_button(label="📥 Baixar JSON Personalizado", data=st.session_state.export_data, file_name=st.session_state.export_filename, mime="application/json")
        with st.expander("Visualizar JSON Gerado"): st.json(st.session_state.export_data)

def pagina_duplicar_para_coligadas():
    st.header("🔎 Duplicar para Coligadas/Filiais")
    st.info("Esta ferramenta cria novas escalas em lote, ideal para adaptar um arquivo base para diferentes filiais ou coligadas, alterando um prefixo em uma tag.")

    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM jsons ORDER BY name")
    rows = cursor.fetchall()

    if not rows:
        st.warning("Nenhum arquivo no banco de dados. Importe um arquivo primeiro.")
        return

    with st.container(border=True):
        st.markdown("#### 📄 Passo 1: Selecione o Arquivo de Origem")
        options_list = [f"{r[0]} - {r[1]}" for r in rows]
        json_id_str = st.selectbox("Selecione o JSON para usar como base", options_list, key="dup_json_select", index=None, placeholder="Escolha um arquivo...")
    
    if json_id_str:
        selected_id = int(json_id_str.split(" - ")[0])
        selected_name = " - ".join(json_id_str.split(" - ")[1:])
        
        cursor.execute("SELECT data FROM jsons WHERE id=?", (selected_id,))
        result = cursor.fetchone()
        if not result:
            st.error("Arquivo não encontrado no banco de dados."); return

        original_data = json.loads(result[0])
        escalas = original_data.get('escalas', [])

        if not escalas:
            st.warning("O arquivo selecionado não contém 'escalas'.")
        else:
            todas_tags = sorted(list(set(key for esc in escalas for key in esc.keys())))
            with st.container(border=True):
                st.markdown("#### 🏷️ Passo 2: Defina a Regra de Duplicação")
                tag_selecionada = st.selectbox("Selecione a Tag para a busca", todas_tags, key="dup_tag_select")
                col1, col2 = st.columns(2)
                with col1: valor_localizar = st.text_input("Texto a ser localizado (prefixo)", key="dup_search")
                with col2: valor_substituir = st.text_input("Substituir o prefixo por", key="dup_replace")

            if st.button("👁️ Pré-visualizar Duplicação", use_container_width=True):
                dados_preview, novas_escalas = [], []
                if valor_localizar:
                    for esc in original_data.get("escalas", []):
                        valor_original_tag = esc.get(tag_selecionada)
                        if isinstance(valor_original_tag, str) and valor_original_tag.startswith(valor_localizar):
                            nova_escala = copy.deepcopy(esc)
                            valor_antigo_tag = nova_escala[tag_selecionada]
                            novo_valor_tag = valor_substituir + valor_antigo_tag[len(valor_localizar):]
                            nova_escala[tag_selecionada] = novo_valor_tag
                            nome_antigo_escala = nova_escala.get("NOME", "")
                            novo_nome_escala = f"{nome_antigo_escala} (Cópia: {valor_substituir})"
                            nova_escala["NOME"] = novo_nome_escala
                            nova_escala["key"] = uuid.uuid4().hex
                            novas_escalas.append(nova_escala)
                            dados_preview.append({"Nome Original": nome_antigo_escala, "Novo Nome Proposto": novo_nome_escala, f"Valor Original ({tag_selecionada})": valor_antigo_tag, f"Valor Proposto ({tag_selecionada})": novo_valor_tag})
                
                if dados_preview:
                    json_modificado = copy.deepcopy(original_data)
                    json_modificado["escalas"].extend(novas_escalas)
                    st.session_state.update({'dados_preview_dup': dados_preview, 'json_modificado_dup': json_modificado,'novas_escalas_dup': novas_escalas, 'selected_id_dup': selected_id,'selected_name_dup': selected_name})
                else:
                    st.warning("Nenhum registro encontrado com o critério especificado.")
                    if 'dados_preview_dup' in st.session_state: del st.session_state['dados_preview_dup']
            
            if st.session_state.get('dados_preview_dup'):
                with st.container(border=True):
                    st.markdown("#### 📊 Passo 3: Confirme e Salve a Duplicação")
                    st.success(f"Serão **criados {len(st.session_state['dados_preview_dup'])} novos registros** de escala.")
                    st.dataframe(pd.DataFrame(st.session_state['dados_preview_dup']), use_container_width=True)
                    st.divider()
                    col_salvar1, col_salvar2 = st.columns(2)
                    with col_salvar1:
                        st.markdown("##### 💾 Opção 1: Salvar Tudo")
                        st.write("Adiciona as novas escalas ao arquivo original e salva o resultado.")
                        opcao = st.radio("Como deseja salvar?", ["Sobrescrever arquivo existente", "Salvar como novo arquivo"], key="dup_save_option", horizontal=True)
                        novo_nome_tudo = ""
                        if opcao == "Salvar como novo arquivo": novo_nome_tudo = st.text_input("Nome do novo arquivo:", value=st.session_state.get('selected_name_dup', 'arquivo.json').replace(".json", "_duplicado.json"), key="dup_new_name_all")
                        if st.button("Salvar Tudo Agora", key="dup_save_btn_all", use_container_width=True, type="primary"):
                            json_final = st.session_state['json_modificado_dup']
                            if opcao == "Sobrescrever arquivo existente":
                                salvar_no_banco(conn, json_final, nome=st.session_state['selected_name_dup'], selected_id=st.session_state['selected_id_dup'])
                                st.success("✅ Alterações salvas no arquivo original.")
                            elif not novo_nome_tudo.strip(): st.error("❌ Informe um nome para o novo arquivo.")
                            else:
                                if salvar_no_banco(conn, json_final, nome=novo_nome_tudo.strip()):
                                    st.success(f"✅ Novo arquivo '{novo_nome_tudo}' salvo com sucesso!")
                            st.rerun()
                    with col_salvar2:
                        st.markdown("##### 💾 Opção 2: Salvar Somente Novas")
                        st.write("Cria um novo arquivo contendo apenas as escalas geradas.")
                        novo_nome_novas = st.text_input("Nome do novo arquivo:", value=st.session_state.get('selected_name_dup', 'arquivo.json').replace(".json", "_apenas_novas.json"), key="dup_new_name_only")
                        if st.button("Salvar Somente Novas", key="dup_save_btn_only", use_container_width=True):
                            if not novo_nome_novas.strip(): st.error("❌ Informe um nome para o novo arquivo.")
                            else:
                                with st.spinner("Preparando novo arquivo..."):
                                    escalas_novas = st.session_state['novas_escalas_dup']
                                    jornadas_originais = st.session_state['json_modificado_dup'].get('jornadas', {})
                                    horas_originais = st.session_state['json_modificado_dup'].get('horas_adicionais', [])
                                    ids_jornadas_necessarias = set(j_key for esc in escalas_novas for j_key in esc.get('JORNADAS', []))
                                    jornadas_filtradas = {k: v for k, v in jornadas_originais.items() if k in ids_jornadas_necessarias}
                                    json_apenas_novas = {"escalas": escalas_novas, "jornadas": jornadas_filtradas, "horas_adicionais": horas_originais}
                                    if salvar_no_banco(conn, json_apenas_novas, nome=novo_nome_novas.strip()):
                                        st.success(f"✅ Novo arquivo '{novo_nome_novas}' salvo!")
                                st.rerun()

def pagina_gerar_escalas_csv():
    st.header("📊 Gerar Escalas por CSV")
    st.info("Carregue um arquivo CSV ou XLSX para convertê-lo em um arquivo JSON estruturado.")
    
    uploaded_file = st.file_uploader("Selecione .csv ou .xlsx", type=["csv", "xlsx"], key="csv_uploader")
    process_button = st.button("🚀 Processar Escalas", disabled=(not uploaded_file), use_container_width=True, type="primary")

    if process_button and uploaded_file:
        try:
            with st.spinner('Aguarde... Processando.'):
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)
                st.session_state.processed_df_head = df.head(10)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(uploaded_file.name)[0]
                
                output_filename = f"resultado_{base_filename}_{timestamp}.json"
                log_filename = f"log_unificacoes_{base_filename}_{timestamp}.txt"
                
                output_dir = "output"; os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_filename)
                
                processed_data, log_unificacao = process_file(df, output_path)
                
                st.session_state.output_path = output_path
                st.session_state.log_filename = log_filename
                st.session_state.log_unificacao = log_unificacao

            st.success("✅ Processamento concluído!")
        except Exception as e:
            st.error(f"❌ Erro ao processar o arquivo: {e}")
            if 'output_path' in st.session_state: del st.session_state.output_path
            if 'log_unificacao' in st.session_state: del st.session_state.log_unificacao
            
    if 'processed_df_head' in st.session_state:
        st.subheader("📄 Pré-visualização do Arquivo de Entrada")
        st.dataframe(st.session_state.processed_df_head)
        st.divider() # Adiciona uma linha divisória para separar as seções

    # --- LAYOUT ATUALIZADO ---
    # As seções de Download e Relatório agora aparecem uma abaixo da outra.

    # Seção 1: Download do JSON de resultado
    if 'output_path' in st.session_state:
        st.subheader("⬇️ Download do Resultado")
        try:
            with open(st.session_state.output_path, "rb") as f:
                st.download_button(
                    label=f"📥 Baixar JSON Unificado",
                    data=f,
                    file_name=os.path.basename(st.session_state.output_path),
                    mime="application/json",
                    use_container_width=True
                )
            with st.expander("Visualizar JSON Gerado"):
                with open(st.session_state.output_path, "r", encoding="utf-8") as f:
                    st.json(f.read())
        except FileNotFoundError:
            st.error("Arquivo de resultado não foi encontrado.")

    # Seção 2: Relatório de Unificação
    if 'log_unificacao' in st.session_state:
        st.subheader("📋 Relatório de Unificação")
        
        if st.session_state.log_unificacao:
            log_data = "\n".join(st.session_state.log_unificacao)
            st.download_button(
                label=f"📋 Baixar Log de Unificações",
                data=log_data.encode('utf-8'),
                file_name=st.session_state.log_filename,
                mime="text/plain",
                use_container_width=True,
                help="Este arquivo lista as escalas que foram unificadas por serem duplicatas."
            )
            with st.expander("Visualizar Log de Unificações"):
                st.text(log_data)
        else:
            st.success("Sucesso! Nenhuma escala duplicada foi encontrada para unificar.")

def pagina_excluir_arquivo():
    st.header("🗑️ Excluir Arquivo")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM jsons ORDER BY name")
    files_to_delete = [row[0] for row in cursor.fetchall()]
    if not files_to_delete:
        st.warning("Nenhum arquivo para excluir."); return
        
    file_to_delete = st.selectbox("Arquivo para excluir:", files_to_delete, index=None, placeholder="Selecione...")
    if file_to_delete:
        st.warning(f"Tem certeza que deseja excluir '{file_to_delete}'? Esta ação é irreversível.")
        if st.button("Confirmar Exclusão", type="primary"):
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
        cursor = conn.cursor()
        cursor.execute("SELECT name, data FROM jsons")
        for name, data in cursor.fetchall():
            for escala in json.loads(data).get("escalas", []): dados.append([name, escala.get("NOME", "N/A")])
        if dados:
            df = pd.DataFrame(dados, columns=["Arquivo", "Escala"]); st.dataframe(df, use_container_width=True)
            st.download_button(label="📥 Baixar CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="lista_arquivos_escalas.csv", mime="text/csv")
        else: st.info("Nenhuma escala encontrada.")
    except Exception as e: st.error(f"Erro ao buscar dados: {e}")


# Adicione esta nova função em app.py

def pagina_editor_visual():
    st.header("✏️ Editor Visual de Escalas")
    st.info("Selecione um arquivo e uma escala para visualizar e editar seus detalhes individualmente.")

    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM jsons ORDER BY name")
    files = cursor.fetchall()
    
    if not files:
        st.warning("Nenhum arquivo no banco de dados para editar.")
        return

    # --- Seleção do Arquivo ---
    options_files = {f_id: name for f_id, name in files}
    selected_file_id = st.selectbox(
        "Passo 1: Selecione um arquivo para editar",
        options_files.keys(),
        format_func=lambda f_id: options_files[f_id],
        index=None,
        placeholder="Escolha um arquivo..."
    )

    if not selected_file_id:
        st.stop()

    # Carrega os dados do arquivo selecionado
    cursor.execute("SELECT data FROM jsons WHERE id = ?", (selected_file_id,))
    json_data_str = cursor.fetchone()[0]
    try:
        data = json.loads(json_data_str)
        escalas = data.get("escalas", [])
        jornadas = data.get("jornadas", {})
    except (json.JSONDecodeError, TypeError):
        st.error("O arquivo selecionado parece estar corrompido e não pôde ser lido.")
        st.stop()
    
    if not escalas:
        st.info("Este arquivo não contém escalas para editar.")
        st.stop()

    # --- Seleção da Escala ---
    options_scales = {esc.get("key"): esc.get("NOME", "Escala sem nome") for esc in escalas}
    selected_scale_key = st.selectbox(
        "Passo 2: Selecione uma escala para editar",
        options_scales.keys(),
        format_func=lambda s_key: options_scales[s_key],
        index=None,
        placeholder="Escolha uma escala..."
    )

    if not selected_scale_key:
        st.stop()
    
    # Encontra o índice da escala selecionada para edição
    scale_index = next((i for i, esc in enumerate(escalas) if esc.get("key") == selected_scale_key), None)
    if scale_index is None:
        st.error("Não foi possível encontrar a escala selecionada. Por favor, recarregue a página.")
        st.stop()

    escala_para_editar = escalas[scale_index]

    st.divider()
    st.subheader(f"Editando: {escala_para_editar.get('NOME')}")

    # --- Formulário de Edição ---
    with st.form(key="edit_form"):
        st.markdown("##### Dados Gerais")
        
        col1_form, col2_form = st.columns(2)
        with col1_form:
            novo_nome = st.text_input("Nome da Escala", value=escala_para_editar.get("NOME", ""))
        with col2_form:
            novo_cod = st.text_input("Código da Escala (COD)", value=escala_para_editar.get("COD", ""))
        
        nova_desc = st.text_area("Descrição da Escala", value=escala_para_editar.get("DESC_ESCALA", ""))

        st.divider()
        st.markdown("##### Estrutura Semanal de Jornadas")

        opcoes_jornada = {j_id: j_data.get("NOME_JORNADA", j_id) for j_id, j_data in jornadas.items()}
        dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        
        jornadas_atuais = escala_para_editar.get("JORNADAS", [])
        novas_jornadas_selecionadas = ["" for _ in dias_semana]
        
        if escala_para_editar.get("TIPO") == "SEMANAL" and len(jornadas_atuais) == 7:
            
            # --- LAYOUT ATUALIZADO: 2 COLUNAS POR LINHA ---
            for i in range(0, len(dias_semana), 2):
                col1, col2 = st.columns(2)
                
                # Coluna da Esquerda (ex: Segunda, Quarta, Sexta, Domingo)
                with col1:
                    jornada_atual_dia_1 = jornadas_atuais[i]
                    index_jornada_atual_1 = list(opcoes_jornada.keys()).index(jornada_atual_dia_1) if jornada_atual_dia_1 in opcoes_jornada else 0
                    jornada_selecionada_1 = st.selectbox(
                        label=dias_semana[i],
                        options=list(opcoes_jornada.keys()),
                        format_func=lambda j_id: opcoes_jornada[j_id],
                        index=index_jornada_atual_1,
                        key=f"dia_{i}"
                    )
                    novas_jornadas_selecionadas[i] = jornada_selecionada_1

                # Coluna da Direita (ex: Terça, Quinta, Sábado)
                # Verifica se existe um segundo dia no par (para o caso do Domingo, que fica sozinho)
                if i + 1 < len(dias_semana):
                    with col2:
                        jornada_atual_dia_2 = jornadas_atuais[i+1]
                        index_jornada_atual_2 = list(opcoes_jornada.keys()).index(jornada_atual_dia_2) if jornada_atual_dia_2 in opcoes_jornada else 0
                        jornada_selecionada_2 = st.selectbox(
                            label=dias_semana[i+1],
                            options=list(opcoes_jornada.keys()),
                            format_func=lambda j_id: opcoes_jornada[j_id],
                            index=index_jornada_atual_2,
                            key=f"dia_{i+1}"
                        )
                        novas_jornadas_selecionadas[i+1] = jornada_selecionada_2

        else:
            st.info(f"Tipo de Escala: **{escala_para_editar.get('TIPO', 'Não definido')}**. A edição de jornadas só está disponível para escalas semanais.")
            st.json([opcoes_jornada.get(j_id, j_id) for j_id in jornadas_atuais])
            novas_jornadas_selecionadas = jornadas_atuais

        st.divider()
        submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary")

        if submitted:
            escala_modificada = copy.deepcopy(escala_para_editar)
            escala_modificada["NOME"] = novo_nome
            escala_modificada["COD"] = novo_cod
            escala_modificada["DESC_ESCALA"] = nova_desc
            escala_modificada["JORNADAS"] = novas_jornadas_selecionadas
            
            from processador import calculate_carga_horaria
            escala_modificada["carga_horaria"] = calculate_carga_horaria(novas_jornadas_selecionadas, jornadas)

            data["escalas"][scale_index] = escala_modificada
            
            nome_arquivo = options_files[selected_file_id]
            if salvar_no_banco(conn, data, nome=nome_arquivo, selected_id=selected_file_id):
                st.success(f"✅ Escala '{novo_nome}' salva com sucesso no arquivo '{nome_arquivo}'!")
                st.info("Recarregando em 3 segundos...")
                time.sleep(3)
                st.rerun()
            else:
                st.error("❌ Ocorreu um erro ao salvar as alterações no banco de dados.")


# Adicione esta nova função em app.py

def pagina_editor_jornadas():
    st.header("📕 Editor de Jornadas")
    st.info("Gerencie, edite e visualize todas as jornadas de trabalho utilizadas em seus arquivos.")

    # --- 1. Agregação de Todas as Jornadas ---
    master_jornadas = {}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM jsons")
        all_files_data = cursor.fetchall()
        for row in all_files_data:
            json_data = json.loads(row[0])
            jornadas_no_arquivo = json_data.get("jornadas", {})
            for j_id, j_data in jornadas_no_arquivo.items():
                if j_id not in master_jornadas:
                    master_jornadas[j_id] = j_data
    except Exception as e:
        st.error(f"Erro ao carregar as jornadas do banco de dados: {e}")
        st.stop()
    
    master_jornadas.pop("ID_DSR", None)
    master_jornadas.pop("ID_FOLGA", None)

    if not master_jornadas:
        st.warning("Nenhuma jornada editável encontrada. Processe um arquivo CSV ou importe um JSON primeiro.")
        return

    # --- 2. Seleção da Jornada ---
    options_jornadas = {j_id: data.get("NOME_JORNADA", j_id) for j_id, data in master_jornadas.items()}
    selected_j_id = st.selectbox(
        "Selecione uma jornada para editar",
        options_jornadas.keys(),
        format_func=lambda j_id: options_jornadas[j_id],
        index=None,
        placeholder="Escolha uma jornada..."
    )

    if not selected_j_id:
        st.stop()

    jornada_para_editar = master_jornadas[selected_j_id]
    st.divider()
    st.subheader(f"Editando Jornada: {jornada_para_editar.get('NOME_JORNADA')}")

    # --- LÓGICA DE EDIÇÃO ATUALIZADA ---
    
    horas_atuais = jornada_para_editar.get("HORAS_CONTRATUAIS", [])
    tipo_jornada_atual = "Com Intervalo" if len(horas_atuais) == 4 else "Simples (Entrada/Saída)"
    
    # MOVIDO PARA FORA DO FORMULÁRIO para permitir a atualização dinâmica da tela
    novo_tipo_jornada = st.radio(
        "Tipo de Jornada",
        ["Simples (Entrada/Saída)", "Com Intervalo"],
        index=1 if tipo_jornada_atual == "Com Intervalo" else 0,
        horizontal=True,
    )

    # --- 3. Formulário de Edição ---
    with st.form("edit_jornada_form"):
        novo_nome_jornada = st.text_input("Nome da Jornada", value=jornada_para_editar.get("NOME_JORNADA", ""))
        
        st.markdown("###### Horários:")

        def to_time(time_str):
            try: return datetime.strptime(time_str, "%H:%M").time()
            except (ValueError, TypeError): return time(0, 0)

        # A lógica if/else aqui dentro agora funciona dinamicamente
        if novo_tipo_jornada == "Simples (Entrada/Saída)":
            col1, col2 = st.columns(2)
            h_entrada = col1.time_input("Horário de Entrada", value=to_time(horas_atuais[0] if len(horas_atuais) > 0 else "08:00"))
            h_saida = col2.time_input("Horário de Saída", value=to_time(horas_atuais[-1] if len(horas_atuais) > 1 else "18:00")) # Pega o último item
            novas_horas = [h_entrada.strftime("%H:%M"), h_saida.strftime("%H:%M")]
        else: # Com Intervalo
            col1, col2, col3, col4 = st.columns(4)
            h_entrada = col1.time_input("Entrada", value=to_time(horas_atuais[0] if len(horas_atuais) > 0 else "08:00"))
            h_ini_int = col2.time_input("Início Intervalo", value=to_time(horas_atuais[1] if len(horas_atuais) > 1 else "12:00"))
            h_fim_int = col3.time_input("Fim Intervalo", value=to_time(horas_atuais[2] if len(horas_atuais) > 2 else "13:00"))
            h_saida = col4.time_input("Saída", value=to_time(horas_atuais[3] if len(horas_atuais) > 3 else "18:00"))
            novas_horas = [h_entrada.strftime("%H:%M"), h_ini_int.strftime("%H:%M"), h_fim_int.strftime("%H:%M"), h_saida.strftime("%H:%M")]

        st.divider()
        submitted = st.form_submit_button("💾 Salvar Alterações na Jornada", use_container_width=True, type="primary")

        if submitted:
            with st.spinner("Atualizando jornada em todos os arquivos... Isso pode levar um momento."):
                jornada_modificada = copy.deepcopy(jornada_para_editar)
                jornada_modificada["NOME_JORNADA"] = novo_nome_jornada
                jornada_modificada["HORAS_CONTRATUAIS"] = novas_horas
                
                from processador import generate_periods_from_punches, format_time_to_hhmm
                jornada_modificada["PERIODOS"] = generate_periods_from_punches(novas_horas)
                jornada_modificada["batida_automatica"] = [format_time_to_hhmm(h) for h in novas_horas[1:3]] if len(novas_horas) == 4 else []
                jornada_modificada["PREASSINALA_SOMENTE_BATIDAS_PARES"] = bool(jornada_modificada["batida_automatica"])

                cursor.execute("SELECT id, name, data FROM jsons")
                all_files_to_check = cursor.fetchall()
                arquivos_afetados = 0
                
                for f_id, f_name, file_data_str in all_files_to_check:
                    file_data = json.loads(file_data_str)
                    if selected_j_id in file_data.get("jornadas", {}):
                        file_data["jornadas"][selected_j_id] = jornada_modificada
                        salvar_no_banco(conn, file_data, nome=f_name, selected_id=f_id)
                        arquivos_afetados += 1
                
                st.success(f"✅ Jornada '{novo_nome_jornada}' atualizada com sucesso em {arquivos_afetados} arquivo(s)!")
                st.info("Recarregando em 3 segundos...")
                time.sleep(3)
                st.rerun()
# =====================================================================================
# LÓGICA PRINCIPAL DA APLICAÇÃO (MENU E ROTEAMENTO)
# =====================================================================================

# Substitua toda a sua função main() em app.py por esta versão final

def main():
    """Função principal que organiza a UI e o roteamento."""
    st.sidebar.title("⚙️ Menu")

    PAGES = {
        "📊 Dashboard": pagina_dashboard,
        "✏️ Editor Visual": pagina_editor_visual,
        "📕 Editor de Jornadas": pagina_editor_jornadas,
        "📊 Gerar escalas através de CSV": pagina_gerar_escalas_csv,
        "📝 Edição em Lote": pagina_edicao_em_lote,
        "🔎 Duplicar para coligadas/filiais": pagina_duplicar_para_coligadas,
        "📥 Importar Escala": pagina_importar_escala,
        "🧩 Exportar JSON Personalizado": pagina_exportar_json_personalizado,
        "📁 Exportar Lista de Arquivos e Escalas": pagina_exportar_lista,
        "🗑️ Excluir Arquivo": pagina_excluir_arquivo,
        "📄 Documentação Recursos": pagina_documentacao,
    }

    selection = st.sidebar.radio("Escolha uma opção:", list(PAGES.keys()), key="main_menu")

    # Chama a função da página selecionada
    page_function = PAGES[selection]
    page_function()
if __name__ == "__main__":
    main()
