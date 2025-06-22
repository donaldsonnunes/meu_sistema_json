# app.py (Versão Final e Consolidada)

import streamlit as st
import sqlite3
import pandas as pd
import json
import os
import copy
import uuid
import time
from datetime import datetime, time as dt_time

# --- Configuração da Página ---
st.set_page_config(page_title="Central de Gestão de Escalas", page_icon="⚙️", layout="wide")

# --- Conexão com o Banco de Dados (Cacheado) ---
@st.cache_resource
def get_db_connection():
    if not os.path.exists('output'): os.makedirs('output')
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS jsons (id INTEGER PRIMARY KEY, name TEXT UNIQUE, data TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regras_traducao (
            id INTEGER PRIMARY KEY, nome_regra TEXT, tipo_regra TEXT NOT NULL,
            condicao_texto TEXT, condicao_duracao TEXT,
            condicao_qtde_horarios INTEGER, condicao_sem_dia BOOLEAN,
            formato_saida TEXT NOT NULL, prioridade INTEGER DEFAULT 10
        )
    ''')
    conn.commit()
    return conn

# --- Funções Auxiliares ---
def salvar_no_banco(conn, data, nome, selected_id=None):
    cursor = conn.cursor()
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    try:
        if selected_id:
            cursor.execute("UPDATE jsons SET name = ?, data = ? WHERE id = ?", (nome, json_str, selected_id))
        else:
            cursor.execute("INSERT INTO jsons (name, data) VALUES (?, ?)", (nome, json_str))
        conn.commit(); return True
    except sqlite3.IntegrityError:
        st.error(f"Erro: Um arquivo com o nome '{nome}' já existe."); return False
    except Exception as e:
        st.error(f"Ocorreu um erro ao salvar: {e}"); return False

# ==============================================================================
# DEFINIÇÃO DAS PÁGINAS DA APLICAÇÃO
# ==============================================================================

def pagina_dashboard(conn):
    st.header("📊 Dashboard de Controle")
    st.markdown("Visão geral dos dados e atividade no sistema.")
    try:
        cursor = conn.cursor()
        total_arquivos = cursor.execute("SELECT COUNT(*) FROM jsons").fetchone()[0]
        rows = cursor.execute("SELECT data FROM jsons").fetchall()
        total_escalas, total_jornadas = 0, 0
        for row in rows:
            try:
                json_data = json.loads(row[0])
                total_escalas += len(json_data.get("escalas", []))
                total_jornadas += len(json_data.get("jornadas", {}))
            except: continue
        col1, col2, col3 = st.columns(3)
        col1.metric("Arquivos Salvos", f"{total_arquivos}")
        col2.metric("Total de Escalas", f"{total_escalas}")
        col3.metric("Total de Jornadas", f"{total_jornadas}")
        st.divider()
        st.subheader("📁 Arquivos no Banco de Dados")
        files_data = cursor.execute("SELECT id, name, data FROM jsons ORDER BY name").fetchall()
        if not files_data: st.info("Nenhum arquivo encontrado.")
        else:
            display_data = [{"ID": f["id"], "Nome do Arquivo": f["name"], "Nº de Escalas": len(json.loads(f["data"]).get("escalas",[]))} for f in files_data]
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"Ocorreu um erro ao carregar o dashboard: {e}")

def pagina_gerenciar_regras(conn):
    st.header("⚙️ Gerenciar Regras de Tradução")
    st.info("Crie e gerencie suas regras de tradução. As regras são aplicadas por prioridade (menor para maior).")
    cursor = conn.cursor()
    with st.expander("➕ Adicionar Nova Regra", expanded=True):
        tipo_regra = st.selectbox("1. Escolha o Tipo de Regra", ["Tradução Exata (DE -> PARA)", "Padrão por Duração / Palavra-Chave", "Padrão por Quantidade de Horários"])
        with st.form("form_nova_regra", clear_on_submit=True):
            st.markdown("##### 2. Preencha os Detalhes da Regra")
            nome_regra = st.text_input("Nome da Regra", help="Um nome para você identificar a regra.")
            if tipo_regra == "Tradução Exata (DE -> PARA)":
                texto_original = st.text_area("Texto Original (DE):")
                formato_saida = st.text_area("Texto Padronizado (PARA):")
            elif tipo_regra == "Padrão por Quantidade de Horários":
                cond_qtde = st.number_input("Se a quantidade de horários for exatamente:", min_value=1, value=4)
                cond_sem_dia = st.checkbox("E se NENHUM dia da semana for especificado", value=True)
                formato_saida = st.text_input("Formato do Texto de Saída:", value="SEG A SEX {h1} / {h2} / {h3} / {h4}", help="Use {h1}, {h2}, etc.")
            else:
                col1, col2 = st.columns(2)
                cond_duracao = col1.text_input("Se a duração for de (HH:MM):", placeholder="ex: 12:00", help="Deixe em branco para ignorar.")
                cond_texto = col2.text_input("E o texto contiver (separado por vírgula):", placeholder="ex: (IMPAR), (PAR)")
                formato_saida = st.text_input("Formato do Texto de Saída:", value="12X36 {h1} AS {h2}", help="Use {h1} e {h2}.")
            prioridade = st.number_input("Prioridade", min_value=1, value=10)
            if st.form_submit_button("Adicionar Regra"):
                try:
                    if tipo_regra == "Tradução Exata (DE -> PARA)":
                        cursor.execute("INSERT INTO regras_traducao (nome_regra, tipo_regra, condicao_texto, formato_saida, prioridade) VALUES (?, 'EXATA', ?, ?, ?)", (nome_regra, texto_original, formato_saida, prioridade))
                    elif tipo_regra == "Padrão por Quantidade de Horários":
                        cursor.execute("INSERT INTO regras_traducao (nome_regra, tipo_regra, condicao_qtde_horarios, condicao_sem_dia, formato_saida, prioridade) VALUES (?, 'QUANTIDADE', ?, ?, ?, ?)", (nome_regra, cond_qtde, cond_sem_dia, formato_saida, prioridade))
                    else:
                        cursor.execute("INSERT INTO regras_traducao (nome_regra, tipo_regra, condicao_duracao, condicao_texto, formato_saida, prioridade) VALUES (?, 'DURACAO', ?, ?, ?, ?)", (nome_regra, cond_duracao, cond_texto, formato_saida, prioridade))
                    conn.commit(); st.success("Regra adicionada!"); st.rerun()
                except Exception as e: st.error(f"Erro ao salvar: {e}")
    st.divider()
    st.subheader("Regras Existentes")
    regras = cursor.execute("SELECT * FROM regras_traducao ORDER BY prioridade, nome_regra").fetchall()
    if not regras: st.info("Nenhuma regra encontrada.")
    else:
        for regra in regras:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{regra['nome_regra']}** (Prioridade: {regra['prioridade']})")
                    if regra['tipo_regra'] == 'EXATA': st.code(f"SE encontrar: '{regra['condicao_texto']}'\nENTÃO: '{regra['formato_saida']}'", language=None)
                    elif regra['tipo_regra'] == 'DURACAO': st.code(f"SE duração for '{regra['condicao_duracao']}' E texto contiver '{regra['condicao_texto'] or ''}'\nENTÃO: '{regra['formato_saida']}'", language=None)
                    elif regra['tipo_regra'] == 'QUANTIDADE': st.code(f"SE qtde for {regra['condicao_qtde_horarios']}' E sem dias\nENTÃO: '{regra['formato_saida']}'", language=None)
                with col2:
                    if st.button("🗑️ Excluir", key=f"del_{regra['id']}", use_container_width=True):
                        cursor.execute("DELETE FROM regras_traducao WHERE id = ?", (regra["id"],)); conn.commit(); st.toast("Regra excluída!"); st.rerun()

def pagina_traduzir_csv_com_regras(conn):
    st.header("📄 Traduzir CSV com Regras")
    st.info("Carregue um CSV. O sistema usará as regras definidas em 'Gerenciar Regras' para traduzir o texto.")
    try: from processador import traduzir_horarios
    except ImportError: st.error("Arquivo 'processador.py' não encontrado."); return
    cursor = conn.cursor()
    regras = [dict(row) for row in cursor.execute("SELECT * FROM regras_traducao ORDER BY prioridade").fetchall()]
    uploaded_file = st.file_uploader("1. Carregue seu arquivo CSV", type=["csv"])
    if uploaded_file:
        df = None; successful_config = None
        configs_para_tentar = [{'encoding': 'latin-1', 'sep': ';'}, {'encoding': 'latin-1', 'sep': ','}, {'encoding': 'utf-8', 'sep': ';'}, {'encoding': 'utf-8', 'sep': ','}]
        for config in configs_para_tentar:
            try:
                uploaded_file.seek(0)
                df_tentativa = pd.read_csv(uploaded_file, engine='python', **config)
                if df_tentativa.shape[1] > 0:
                    df = df_tentativa; successful_config = config; break
            except Exception: continue
        if df is None: st.error("Não foi possível ler o arquivo CSV."); return
        df = df.drop(columns=[col for col in df.columns if 'Unnamed:' in str(col)], errors='ignore')
        st.subheader("Pré-visualização"); st.dataframe(df.head())
        colunas = df.columns.tolist()
        default_col_name = "DFHORDESCRICAO"
        default_index = colunas.index(default_col_name) if default_col_name in colunas else 0
        coluna_selecionada = st.selectbox("2. Selecione a coluna a ser traduzida", colunas, index=default_index)
        if st.button("3. Aplicar Regras e Traduzir", use_container_width=True, type="primary"):
            with st.spinner("Analisando e traduzindo..."):
                df_resultado, log_depuracao = traduzir_horarios(df, coluna_selecionada, regras)
                st.session_state.df_traduzido = df_resultado
                csv_resultado = df_resultado.to_csv(index=False, sep=successful_config['sep']).encode(successful_config['encoding'], errors='ignore')
                st.session_state.csv_traduzido = csv_resultado
                if log_depuracao:
                    st.session_state.log_depuracao_data = "\n".join(log_depuracao).encode('utf-8')
                    st.session_state.log_depuracao_filename = f"log_depuracao_{uploaded_file.name}.txt"
                elif 'log_depuracao_data' in st.session_state: del st.session_state.log_depuracao_data
            st.success("Tradução concluída!")
    if 'df_traduzido' in st.session_state and uploaded_file:
        st.subheader("Resultado da Tradução"); st.dataframe(st.session_state.df_traduzido)
        col1, col2 = st.columns(2)
        with col1: st.download_button(label="📥 Baixar CSV Traduzido", data=st.session_state.csv_traduzido, file_name=f"traduzido_{uploaded_file.name}", mime="text/csv", use_container_width=True)
        with col2:
            if 'log_depuracao_data' in st.session_state:
                st.download_button(label="📋 Baixar Análise da Tradução (.txt)", data=st.session_state.log_depuracao_data, file_name=st.session_state.log_depuracao_filename, mime="text/plain", use_container_width=True)

def pagina_gerar_escalas_csv(conn):
    st.header("📊 Gerar Escalas por CSV")
    st.info("Carregue um arquivo com descrições JÁ PADRONIZADAS para convertê-lo em um arquivo JSON.")
    try: from processador import process_file
    except ImportError: st.error("Arquivo 'processador.py' não encontrado."); return
    uploaded_file = st.file_uploader("Selecione .csv ou .xlsx", type=["csv", "xlsx"], key="gen_csv_uploader")
    if uploaded_file and st.button("🚀 Processar Escalas", use_container_width=True, type="primary"):
        with st.spinner('Processando...'):
            try:
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file, sep=None, engine='python')
                timestamp, base_filename = datetime.now().strftime("%Y%m%d_%H%M%S"), os.path.splitext(uploaded_file.name)[0]
                output_filename, log_filename = f"resultado_{base_filename}_{timestamp}.json", f"log_unificacoes_{base_filename}_{timestamp}.txt"
                output_dir = "output"; os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_filename)
                processed_data, log_unificacao = process_file(df, output_path)
                st.session_state.gen_output_path, st.session_state.gen_log_unificacao, st.session_state.gen_log_filename = output_path, log_unificacao, log_filename
                st.success("✅ Processamento concluído!")
            except Exception as e: st.error(f"❌ Erro: {e}")
    if 'gen_output_path' in st.session_state:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⬇️ Download do Resultado JSON")
            with open(st.session_state.gen_output_path, "rb") as f:
                st.download_button(label=f"📥 Baixar {os.path.basename(st.session_state.gen_output_path)}", data=f, file_name=os.path.basename(st.session_state.gen_output_path), mime="application/json", use_container_width=True)
        with col2:
            st.subheader("📋 Relatório de Unificação")
            if st.session_state.gen_log_unificacao:
                log_data = "\n".join(st.session_state.gen_log_unificacao)
                st.download_button(label=f"📋 Baixar Log de Unificações", data=log_data.encode('utf-8'), file_name=st.session_state.gen_log_filename, mime="text/plain", use_container_width=True)
            else: st.success("Nenhuma escala duplicada foi encontrada.")

def _pagina_edicao_em_massa(conn, titulo_pagina, chave_sufixo, formato_novo_nome, sufixo_arquivo_novo):
    st.header(titulo_pagina)
    st.info("Esta ferramenta cria novas escalas em lote com base na substituição de um prefixo em uma tag específica.")
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, name FROM jsons ORDER BY name").fetchall()
    if not rows: st.warning("Nenhum arquivo no banco de dados."); return
    options_list = {r["id"]: r["name"] for r in rows}
    json_id = st.selectbox("Selecione o JSON para editar", options_list.keys(), format_func=lambda id: options_list.get(id), key=f"json_select_{chave_sufixo}", index=None, placeholder="Escolha um arquivo...")
    if json_id:
        selected_name = options_list[json_id]
        result = cursor.execute("SELECT data FROM jsons WHERE id=?", (json_id,)).fetchone()
        if not result: st.error("Arquivo não encontrado."); return
        original_data = json.loads(result[0])
        escalas = original_data.get('escalas', [])
        if not escalas: st.warning("O arquivo não contém 'escalas'."); return
        todas_tags = sorted(list(set(key for esc in escalas for key in esc.keys())))
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            tag_selecionada, valor_localizar, valor_substituir = col1.selectbox("Tag", todas_tags, key=f"tag_{chave_sufixo}"), col2.text_input("Localizar prefixo", key=f"search_{chave_sufixo}"), col3.text_input("Substituir por", key=f"replace_{chave_sufixo}")
            if st.button("👁️ Pré-visualizar", use_container_width=True, key=f"preview_{chave_sufixo}"):
                dados_preview, novas_escalas = [], []
                if valor_localizar:
                    for esc in original_data.get("escalas", []):
                        valor_original = esc.get(tag_selecionada)
                        if isinstance(valor_original, str) and valor_original.startswith(valor_localizar):
                            nova_escala = copy.deepcopy(esc)
                            novo_valor = valor_substituir + valor_original[len(valor_localizar):]
                            nova_escala[tag_selecionada] = novo_valor
                            novo_nome = formato_novo_nome.format(nome_antigo=nova_escala.get("NOME", ""), valor_substituir=valor_substituir)
                            nova_escala["NOME"], nova_escala["key"] = novo_nome, uuid.uuid4().hex
                            novas_escalas.append(nova_escala)
                            dados_preview.append({"Nome Original": esc.get("NOME"), "Novo Nome": novo_nome, f"Tag Original": valor_original, f"Tag Proposta": novo_valor})
                if dados_preview:
                    json_modificado = copy.deepcopy(original_data); json_modificado["escalas"].extend(novas_escalas)
                    st.session_state[f'preview_{chave_sufixo}'] = pd.DataFrame(dados_preview)
                    st.session_state[f'json_mod_{chave_sufixo}'] = json_modificado
                else: st.warning("Nenhum registro encontrado.")
        if f'preview_{chave_sufixo}' in st.session_state:
            with st.container(border=True):
                st.markdown("#### Confirme e Salve"); st.dataframe(st.session_state[f'preview_{chave_sufixo}'], use_container_width=True)
                opcao = st.radio("Como salvar?", ["Sobrescrever arquivo", "Salvar como novo"], key=f"save_opt_{chave_sufixo}", horizontal=True)
                novo_nome_arquivo = st.text_input("Nome do novo arquivo:", value=selected_name.replace(".json", f"_{sufixo_arquivo_novo}.json"), key=f"new_name_{chave_sufixo}") if opcao == "Salvar como novo" else ""
                if st.button("Salvar Agora", key=f"save_btn_{chave_sufixo}", type="primary"):
                    json_final = st.session_state[f'json_mod_{chave_sufixo}']
                    id_salvar, nome_salvar = (json_id, selected_name) if opcao == "Sobrescrever arquivo" else (None, novo_nome_arquivo.strip())
                    if not nome_salvar: st.error("Informe um nome para o novo arquivo.")
                    elif salvar_no_banco(conn, json_final, nome=nome_salvar, selected_id=id_salvar):
                        st.success("Arquivo salvo!"); [st.session_state.pop(key) for key in list(st.session_state.keys()) if key.endswith(chave_sufixo)]; time.sleep(1); st.rerun()

def pagina_edicao_em_lote(conn):
    _pagina_edicao_em_massa(conn, "📝 Edição em Lote", "lote", "{nome_antigo} - {valor_substituir}", "modificado")

def pagina_duplicar_para_coligadas(conn):
    _pagina_edicao_em_massa(conn, "🔎 Duplicar para Coligadas/Filiais", "dup", "{nome_antigo} (Cópia: {valor_substituir})", "duplicado")

def pagina_importar_escala(conn):
    st.header("📥 Importar Escala JSON")
    uploaded_file = st.file_uploader("Escolha um arquivo .json", type="json")
    if uploaded_file:
        try:
            data = json.load(uploaded_file)
            st.success("Arquivo pré-visualizado. Clique abaixo para salvar."); st.json(data, expanded=False)
            if st.button("Salvar no Banco de Dados", type="primary"):
                if salvar_no_banco(conn, data, nome=uploaded_file.name): st.success(f"Arquivo '{uploaded_file.name}' salvo!"); st.rerun()
        except Exception as e: st.error(f"Ocorreu um erro: {e}")

def pagina_exportar_json_personalizado(conn):
    st.header("🧩 Exportar JSON Personalizado")
    cursor = conn.cursor()
    files = cursor.execute("SELECT id, name FROM jsons ORDER BY name").fetchall()
    if not files: st.warning("Nenhum arquivo JSON disponível."); return
    options_files = {f['id']: f['name'] for f in files}
    selected_file_id = st.selectbox("1. Arquivo de origem:", options_files.keys(), format_func=lambda id: options_files.get(id), index=None, placeholder="Escolha um arquivo...")
    if selected_file_id:
        json_data = json.loads(cursor.execute("SELECT data FROM jsons WHERE id = ?", (selected_file_id,)).fetchone()['data'])
        scale_options = {s.get("key"): s.get("NOME") for s in json_data.get("escalas", [])}
        select_all = st.checkbox("Selecionar todas as escalas", value=False)
        default_selection = list(scale_options.keys()) if select_all else []
        selected_keys = st.multiselect("2. Selecione as escalas:", options=scale_options.keys(), format_func=lambda k: scale_options.get(k), default=default_selection)
        if selected_keys and st.button("Gerar JSON Personalizado", type="primary"):
            escalas_selecionadas = [s for s in json_data.get("escalas", []) if s.get("key") in selected_keys]
            jornadas_usadas = {j_key for esc in escalas_selecionadas for j_key in esc.get("JORNADAS", [])}
            jornadas_filtradas = {k: v for k, v in json_data.get("jornadas", {}).items() if k in jornadas_usadas}
            new_json = {"escalas": escalas_selecionadas, "jornadas": jornadas_filtradas, "horas_adicionais": json_data.get("horas_adicionais", [])}
            st.session_state.export_data = json.dumps(new_json, indent=4, ensure_ascii=False)
            st.session_state.export_filename = f"personalizado_{options_files[selected_file_id]}"
    if 'export_data' in st.session_state:
        st.download_button("📥 Baixar JSON", st.session_state.export_data, st.session_state.export_filename, "application/json")

def pagina_exportar_lista(conn):
    st.header("📁 Exportar Lista de Escalas")
    rows = conn.cursor().execute("SELECT name, data FROM jsons ORDER BY name").fetchall()
    if not rows: st.warning("Nenhum arquivo no banco de dados."); return
    data_list = []
    for row in rows:
        try:
            for esc in json.loads(row['data']).get("escalas", []): data_list.append([row['name'], esc.get("NOME", "Sem nome")])
        except: data_list.append([row['name'], "ERRO"])
    df = pd.DataFrame(data_list, columns=["Arquivo", "Escala"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("📥 Baixar como CSV", df.to_csv(index=False, sep=';').encode('latin-1'), "lista_escalas.csv", "text/csv")

def pagina_excluir_arquivo(conn):
    st.header("🗑️ Excluir Arquivo")
    cursor = conn.cursor()
    files = cursor.execute("SELECT id, name FROM jsons ORDER BY name").fetchall()
    if not files: st.warning("Nenhum arquivo no banco de dados."); return
    file_map = {f['id']: f['name'] for f in files}
    selected_id = st.selectbox("Selecione um arquivo para excluir:", file_map.keys(), format_func=lambda id: file_map.get(id), index=None, placeholder="Escolha um arquivo...")
    if selected_id and st.button("Confirmar Exclusão", type="danger"):
        cursor.execute("DELETE FROM jsons WHERE id = ?", (selected_id,)); conn.commit()
        st.success(f"Arquivo '{file_map[selected_id]}' excluído."); time.sleep(1); st.rerun()

def pagina_documentacao(conn):
    st.header("📄 Documentação dos Recursos")
    # (Conteúdo completo da documentação que criamos anteriormente vai aqui)
    st.markdown("Bem-vindo! Esta ferramenta foi desenvolvida para processar, gerenciar e otimizar escalas de trabalho de forma inteligente.")

# Cole este bloco de código inteiro dentro do seu app.py

def _pagina_edicao_em_massa(conn, titulo_pagina, chave_sufixo, formato_novo_nome, sufixo_arquivo_novo):
    """
    Função genérica e refatorada para lidar com duplicação e edição em lote.
    """
    st.header(titulo_pagina)
    st.info("Esta ferramenta cria novas escalas em lote com base na substituição de um prefixo em uma tag específica.")
    
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, name FROM jsons ORDER BY name").fetchall()
    if not rows: st.warning("Nenhum arquivo no banco de dados."); return
    
    options_list = {r["id"]: r["name"] for r in rows}
    json_id = st.selectbox("1. Selecione o JSON de origem", options_list.keys(), format_func=lambda id: options_list.get(id), key=f"json_select_{chave_sufixo}", index=None, placeholder="Escolha um arquivo...")
    
    if json_id:
        selected_name = options_list[json_id]
        result = cursor.execute("SELECT data FROM jsons WHERE id=?", (json_id,)).fetchone()
        if not result: st.error("Arquivo não encontrado."); return
        
        original_data = json.loads(result[0])
        escalas = original_data.get('escalas', [])
        if not escalas: st.warning("O arquivo não contém 'escalas'."); return
        
        todas_tags = sorted(list(set(key for esc in escalas for key in esc.keys())))
        
        with st.container(border=True):
            st.markdown("##### 2. Defina a Regra de Substituição")
            col1, col2, col3 = st.columns(3)
            tag_selecionada = col1.selectbox("Buscar na Tag:", todas_tags, key=f"tag_{chave_sufixo}")
            valor_localizar = col2.text_input("Texto a localizar (prefixo):", key=f"search_{chave_sufixo}")
            valor_substituir = col3.text_input("Substituir prefixo por:", key=f"replace_{chave_sufixo}")
        
        if st.button("👁️ Pré-visualizar Alterações", use_container_width=True, key=f"preview_{chave_sufixo}"):
            dados_preview, novas_escalas = [], []
            if valor_localizar:
                for esc in original_data.get("escalas", []):
                    valor_original = esc.get(tag_selecionada)
                    if isinstance(valor_original, str) and valor_original.startswith(valor_localizar):
                        nova_escala = copy.deepcopy(esc)
                        novo_valor = valor_substituir + valor_original[len(valor_localizar):]
                        nova_escala[tag_selecionada] = novo_valor
                        novo_nome = formato_novo_nome.format(nome_antigo=nova_escala.get("NOME", ""), valor_substituir=valor_substituir)
                        nova_escala["NOME"], nova_escala["key"] = novo_nome, uuid.uuid4().hex
                        novas_escalas.append(nova_escala)
                        dados_preview.append({"Nome Original": esc.get("NOME"), "Novo Nome": novo_nome, f"Tag Original": valor_original, f"Tag Proposta": novo_valor})
            
            if dados_preview:
                json_modificado = copy.deepcopy(original_data)
                json_modificado["escalas"].extend(novas_escalas)
                st.session_state[f'preview_{chave_sufixo}'] = pd.DataFrame(dados_preview)
                st.session_state[f'json_mod_{chave_sufixo}'] = json_modificado
            else:
                st.warning("Nenhum registro encontrado com o critério especificado.")
                if f'preview_{chave_sufixo}' in st.session_state: del st.session_state[f'preview_{chave_sufixo}']
        
        if f'preview_{chave_sufixo}' in st.session_state:
            with st.container(border=True):
                st.markdown("#### 3. Confirme e Salve")
                st.dataframe(st.session_state[f'preview_{chave_sufixo}'], use_container_width=True)
                
                opcao = st.radio("Como deseja salvar?", ["Sobrescrever arquivo existente", "Salvar como novo arquivo"], key=f"save_opt_{chave_sufixo}", horizontal=True)
                novo_nome_arquivo = ""
                if opcao == "Salvar como novo arquivo":
                    default_name = selected_name.replace(".json", f"_{sufixo_arquivo_novo}.json")
                    novo_nome_arquivo = st.text_input("Nome do novo arquivo:", value=default_name, key=f"new_name_{chave_sufixo}")
                
                if st.button("Salvar Agora", key=f"save_btn_{chave_sufixo}", type="primary"):
                    json_final = st.session_state[f'json_mod_{chave_sufixo}']
                    id_salvar, nome_salvar = (json_id, selected_name) if opcao == "Sobrescrever arquivo existente" else (None, novo_nome_arquivo.strip())
                    if not nome_salvar:
                        st.error("Informe um nome para o novo arquivo.")
                    elif salvar_no_banco(conn, json_final, nome=nome_salvar, selected_id=id_salvar):
                        st.success("Arquivo salvo com sucesso!")
                        for key in list(st.session_state.keys()):
                            if chave_sufixo in key: del st.session_state[key]
                        time.sleep(1)
                        st.rerun()

def pagina_duplicar_para_coligadas(conn):
    _pagina_edicao_em_massa(
        conn,
        titulo_pagina="🔎 Duplicar para Coligadas/Filiais",
        chave_sufixo="dup",
        formato_novo_nome="{nome_antigo} (Cópia: {valor_substituir})",
        sufixo_arquivo_novo="duplicado"
    )

def pagina_exportar_json_personalizado(conn):
    st.header("🧩 Exportar JSON Personalizado")
    cursor = conn.cursor()
    files = cursor.execute("SELECT id, name FROM jsons ORDER BY name").fetchall()
    if not files: st.warning("Nenhum arquivo JSON disponível."); return

    options_files = {f['id']: f['name'] for f in files}
    selected_file_id = st.selectbox("1. Arquivo de origem:", options_files.keys(), format_func=lambda id: options_files.get(id), index=None, placeholder="Escolha um arquivo...")

    if selected_file_id:
        json_data = json.loads(cursor.execute("SELECT data FROM jsons WHERE id = ?", (selected_file_id,)).fetchone()['data'])
        scale_options = {s.get("key"): s.get("NOME", "Sem nome") for s in json_data.get("escalas", []) if s.get("key")}
        
        select_all = st.checkbox("Selecionar todas as escalas", value=False)
        default_selection = list(scale_options.keys()) if select_all else []
        
        selected_keys = st.multiselect("2. Selecione as escalas:", options=scale_options.keys(), format_func=lambda k: scale_options.get(k, k), default=default_selection)
        
        if st.button("Gerar JSON Personalizado", type="primary", use_container_width=True):
            if not selected_keys:
                st.warning("Nenhuma escala selecionada.")
                st.stop()
            
            escalas_selecionadas = [s for s in json_data.get("escalas", []) if s.get("key") in selected_keys]
            jornadas_usadas = {j_key for esc in escalas_selecionadas for j_key in esc.get("JORNADAS", [])}
            jornadas_filtradas = {k: v for k, v in json_data.get("jornadas", {}).items() if k in jornadas_usadas}
            
            new_json = {"escalas": escalas_selecionadas, "jornadas": jornadas_filtradas, "horas_adicionais": json_data.get("horas_adicionais", [])}
            
            st.session_state.export_data = json.dumps(new_json, indent=4, ensure_ascii=False)
            st.session_state.export_filename = f"personalizado_{options_files[selected_file_id]}"
            
    if 'export_data' in st.session_state and st.session_state.export_data:
        st.subheader("⬇️ Download do Resultado")
        st.download_button("📥 Baixar JSON", st.session_state.export_data, st.session_state.export_filename, "application/json", use_container_width=True)


# ==============================================================================
# FUNÇÃO PRINCIPAL (MAIN)
# ==============================================================================
def main():
    st.sidebar.title("⚙️ Menu de Ferramentas")
    conn = get_db_connection()
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "📊 Dashboard"

# Dentro da função main() em app.py

    PAGES = {
        "📊 Dashboard": pagina_dashboard,
        "--- TRADUÇÃO E CRIAÇÃO ---": None,
        "⚙️ Gerenciar Regras de Tradução": pagina_gerenciar_regras,
        "📄 Traduzir CSV com Regras": pagina_traduzir_csv_com_regras,
        "📊 Gerar Escalas por CSV": pagina_gerar_escalas_csv,
        "--- EDIÇÃO E GESTÃO ---": None,
        "📝 Edição em Lote": pagina_edicao_em_lote, # RESTAURADO
        "🔎 Duplicar para Coligadas": pagina_duplicar_para_coligadas, # RESTAURADO
        "🧩 Exportar JSON Personalizado": pagina_exportar_json_personalizado, # RESTAURADO
        "--- ARQUIVOS ---": None,
        "📁 Exportar Lista de Escalas": pagina_exportar_lista,
        "🗑️ Excluir Arquivo": pagina_excluir_arquivo,
        "--- AJUDA ---": None,
        "📄 Documentação Recursos": pagina_documentacao,
    }

    for page_name, page_func in PAGES.items():
        if "---" in page_name:
            st.sidebar.divider()
            st.sidebar.caption(page_name.replace("---", "").strip())
        else:
            button_type = "primary" if st.session_state.current_page == page_name else "secondary"
            if st.sidebar.button(page_name, use_container_width=True, type=button_type):
                st.session_state.current_page = page_name
                st.rerun()
    
    page_to_call = PAGES[st.session_state.current_page]
    if page_to_call is not None:
        page_to_call(conn)

if __name__ == '__main__':
    main()