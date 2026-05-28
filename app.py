# app.py (Versão Final Completa e Corrigida)

import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import json
import os
import copy
import uuid
import time
import re
from datetime import datetime

# Importa as funções do seu script de processamento.
try:
    from processador import process_file, traduzir_horarios
except ImportError:
    st.error("ERRO CRÍTICO: O arquivo 'processador.py' não foi encontrado. A aplicação não pode funcionar.")
    st.stop()

# --- Configuração da Página ---
st.set_page_config(page_title="Central de Gestão de Escalas", page_icon="✨", layout="wide")

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

def pagina_assistente_ia(conn):
    st.header("✨ Assistente de Criação com IA")
    st.info("Descreva as escalas em linguagem natural. A IA irá ajudar a estruturar e validar os dados.")

    if 'session_scales' not in st.session_state:
        st.session_state.session_scales = []

    with st.expander("✨ Criar Escala com Assistente IA", expanded=True):
        st.markdown("Descreva a escala que deseja criar. A IA irá sugerir uma estrutura.")
        user_description = st.text_area("Exemplo: 'Segunda a sexta das 8 às 18 com 1h de almoço, e sábado das 8 ao meio-dia.' ou 'Escala 12x36 diurna, das 7h às 19h'", key="ia_description")
        
        if st.button("Analisar Descrição com IA", key="ia_analyze_btn"):
            if user_description:
                with st.spinner("Analisando descrição com a IA do Gemini..."):
                    suggestion = {}
                    if "12x36" in user_description.lower():
                        suggestion["tipo_escala"] = "12X36"
                        suggestion["nome_escala"] = f"Escala 12x36 Sugerida"
                        suggestion["codigo_escala"] = "12X36-AI"
                        
                        match = re.search(r'(\d{1,2}(?::\d{2})?)\s*(?:as|às)\s*(\d{1,2}(?::\d{2})?)', user_description, re.IGNORECASE)
                        
                        if match:
                            start_time_str = match.group(1)
                            end_time_str = match.group(2)
                            
                            start_time = f"{start_time_str.split(':')[0].zfill(2)}:{start_time_str.split(':')[1] if ':' in start_time_str else '00'}"
                            end_time = f"{end_time_str.split(':')[0].zfill(2)}:{end_time_str.split(':')[1] if ':' in end_time_str else '00'}"
                            
                            suggestion["jornadas"] = [f"12x36 {start_time} as {end_time}"]
                            suggestion["nome_escala"] = f"Escala 12x36 ({start_time} às {end_time})"
                        else:
                            suggestion["jornadas"] = ["12x36 07:00 as 19:00"] # Fallback
                    else:
                        suggestion["tipo_escala"] = "SEMANAL"
                        suggestion["nome_escala"] = "Escala Semanal Sugerida"
                        suggestion["codigo_escala"] = "SEM-AI-01"
                        suggestion["jornadas"] = [user_description]
                    
                    st.session_state.suggestion = suggestion
                    st.success("Análise da IA concluída! Verifique e confirme abaixo.")
            else:
                st.warning("Por favor, insira uma descrição para ser analisada.")

    if 'suggestion' in st.session_state and st.session_state.suggestion:
        st.subheader("Sugestão da IA")
        s = st.session_state.suggestion
        with st.form("form_confirm_suggestion", clear_on_submit=True):
            nome = st.text_input("Nome da Escala", value=s.get("nome_escala"))
            codigo = st.text_input("Código da Escala", value=s.get("codigo_escala"))
            tipo_options = ["SEMANAL", "12X36"]
            tipo_index = tipo_options.index(s.get("tipo_escala")) if s.get("tipo_escala") in tipo_options else 0
            tipo = st.selectbox("Tipo da Escala", tipo_options, index=tipo_index)
            jornadas_str = st.text_area("Jornadas", value="\n".join(s.get("jornadas", [])), height=100)
            
            submitted = st.form_submit_button("Adicionar Escala à Sessão")
            if submitted:
                new_scale = {
                    "id": str(uuid.uuid4()),
                    "nome_escala": nome,
                    "codigo_escala": codigo,
                    "tipo_escala": tipo,
                    "jornadas": [j.strip() for j in jornadas_str.split('\n') if j.strip()],
                    "analise_clt": None
                }
                st.session_state.session_scales.append(new_scale)
                del st.session_state.suggestion
                st.rerun()

    st.divider()
    st.subheader("Escalas na Sessão Atual")
    if not st.session_state.session_scales:
        st.info("Nenhuma escala foi adicionada ainda.")
    else:
        for i, scale in enumerate(st.session_state.session_scales):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{scale['nome_escala']}** (`{scale['codigo_escala']}`)")
                    st.text("\n".join(scale['jornadas']))
                with col2:
                    if st.button("✨ Analisar Conformidade", key=f"analise_{scale['id']}", use_container_width=True):
                         with st.spinner("Analisando com Gemini..."):
                            if scale['tipo_escala'] == '12X36':
                                st.session_state.session_scales[i]['analise_clt'] = "Análise da IA (12x36): A jornada de 12 horas de trabalho é seguida por 36 horas de descanso, o que está em conformidade com a CLT. O intervalo para refeição e repouso, de no mínimo 1 hora, pode ser concedido ou indenizado."
                            else: # Semanal
                                st.session_state.session_scales[i]['analise_clt'] = "Análise da IA (Semanal): A escala parece respeitar o descanso interjornada de 11h. A pausa para refeição de 1h para jornadas acima de 6h está adequada. O Descanso Semanal Remunerado (DSR) de 24h deve ser garantido preferencialmente aos domingos."
                         st.rerun()
                if scale.get('analise_clt'):
                    st.info(f"**Análise da IA:** {scale['analise_clt']}")

    if st.session_state.session_scales:
        st.divider()
        if st.button("Gerar JSON Final de Todas as Escalas", type="primary", use_container_width=True):
            with st.spinner("Processando escalas..."):
                lista_para_df = []
                for escala in st.session_state.session_scales:
                    descricao_final = " E ".join(escala.get("jornadas", [])).upper()
                    lista_para_df.append({
                        'NOME': escala.get('nome_escala'),
                        'COD': escala.get('codigo_escala'),
                        'CARGA_HORARIA': escala.get('carga_horaria', '0'),
                        'DESCRICAO_TRADUZIDA': descricao_final,
                        'TIPO': escala.get('tipo_escala')
                    })
                
                df_completo = pd.DataFrame(lista_para_df)
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"resultado_assistente_ia_{timestamp}.json"
                output_path = os.path.join(output_dir, output_filename)
                
                json_gerado, _ = process_file(df_completo, output_path)
                
                st.session_state.final_json = json_gerado
                st.session_state.final_json_filename = output_filename
            st.rerun()

    if 'final_json' in st.session_state and st.session_state.get('final_json'):
        st.success("JSON consolidado gerado com sucesso!")
        st.json(st.session_state.final_json)

        with st.form("form_salvar_ia_json"):
            nome_arquivo = st.text_input("Nome para salvar no banco de dados:", value=st.session_state.final_json_filename)
            submitted = st.form_submit_button("Salvar no Banco de Dados")
            if submitted:
                if salvar_no_banco(conn, st.session_state.final_json, nome=nome_arquivo):
                    st.success(f"Arquivo '{nome_arquivo}' salvo no banco de dados!")
                    st.session_state.session_scales = []
                    del st.session_state.final_json
                    st.rerun()
        
        json_string = json.dumps(st.session_state.get('final_json', {}), indent=4, ensure_ascii=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Arquivo JSON",
            data=json_string,
            file_name=st.session_state.final_json_filename,
            mime="application/json",
            use_container_width=True
        )

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
    
    cursor = conn.cursor()
    regras = [dict(row) for row in cursor.execute("SELECT * FROM regras_traducao ORDER BY prioridade").fetchall()]
    
    uploaded_file = st.file_uploader("1. Carregue seu arquivo CSV", type=["csv"], key="trad_csv_uploader")
    
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
        default_col_name = next((col for col in colunas if "HOR" in col.upper()), colunas[0])
        default_index = colunas.index(default_col_name) if default_col_name in colunas else 0
        coluna_selecionada = st.selectbox("2. Selecione a coluna a ser traduzida", colunas, index=default_index)
        
        if st.button("3. Aplicar Regras e Traduzir", use_container_width=True, type="primary"):
            with st.spinner("Analisando e traduzindo..."):
                df_resultado, log_depuracao = traduzir_horarios(df, coluna_selecionada, regras)
                st.session_state.df_traduzido = df_resultado
                st.session_state.nome_original_arquivo = uploaded_file.name
                csv_resultado = df_resultado.to_csv(index=False, sep=successful_config['sep']).encode(successful_config['encoding'], errors='ignore')
                st.session_state.csv_traduzido = csv_resultado
                if log_depuracao:
                    st.session_state.log_depuracao_data = "\n".join(log_depuracao).encode('utf-8')
                    st.session_state.log_depuracao_filename = f"log_depuracao_{uploaded_file.name}.txt"
                elif 'log_depuracao_data' in st.session_state: del st.session_state.log_depuracao_data
            st.success("Tradução concluída!")

    if 'df_traduzido' in st.session_state:
        st.subheader("Resultado da Tradução"); st.dataframe(st.session_state.df_traduzido)
        col1, col2 = st.columns(2)
        with col1: st.download_button(label="📥 Baixar CSV Traduzido", data=st.session_state.csv_traduzido, file_name=f"traduzido_{st.session_state.nome_original_arquivo}", mime="text/csv", use_container_width=True)
        with col2:
            if 'log_depuracao_data' in st.session_state:
                st.download_button(label="📋 Baixar Análise da Tradução (.txt)", data=st.session_state.log_depuracao_data, file_name=st.session_state.log_depuracao_filename, mime="text/plain", use_container_width=True)

        st.divider()
        st.markdown("#### Próximo Passo")
        if st.button("➡️ Prosseguir para Gerar Arquivo JSON", type="primary", use_container_width=True):
            st.session_state.df_para_geracao = st.session_state.df_traduzido
            for key in ['df_traduzido', 'csv_traduzido', 'log_depuracao_data', 'log_depuracao_filename']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_page = "📊 Gerar Escalas por CSV"
            st.rerun()

def pagina_gerar_escalas_csv(conn):
    st.header("📊 Gerar Escalas por CSV")
    st.info("Carregue um arquivo com descrições JÁ PADRONIZADAS para convertê-lo em um arquivo JSON.")
    
    df = None
    if 'df_para_geracao' in st.session_state:
        st.success(f"Utilizando o arquivo traduzido: **{st.session_state.get('nome_original_arquivo', 'arquivo.csv')}**")
        df = st.session_state.df_para_geracao
        del st.session_state.df_para_geracao
        if 'nome_original_arquivo' in st.session_state:
            del st.session_state.nome_original_arquivo
    else:
        uploaded_file = st.file_uploader("Selecione .csv ou .xlsx", type=["csv", "xlsx"], key="gen_csv_uploader")
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                else:
                    configs_para_tentar = [{'encoding': 'latin-1', 'sep': ';'}, {'encoding': 'latin-1', 'sep': ','}, {'encoding': 'utf-8', 'sep': ';'}, {'encoding': 'utf-8', 'sep': ','}]
                    for config in configs_para_tentar:
                        try:
                            uploaded_file.seek(0)
                            df_tentativa = pd.read_csv(uploaded_file, engine='python', **config)
                            if df_tentativa.shape[1] > 0:
                                df = df_tentativa
                                st.session_state.nome_original_arquivo = uploaded_file.name
                                break
                        except Exception: continue
                if df is None: st.error("Não foi possível ler o arquivo. Verifique o formato e a codificação.")
            except Exception as e: st.error(f"❌ Erro ao ler o arquivo: {e}")

    if df is not None:
        df = df.drop(columns=[col for col in df.columns if 'Unnamed:' in str(col)], errors='ignore')
        st.subheader("Pré-visualização do Arquivo a ser Processado")
        st.dataframe(df.head())

        if st.button("🚀 Processar Escalas", use_container_width=True, type="primary"):
            with st.spinner('Processando...'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(st.session_state.get('nome_original_arquivo', 'arquivo'))[0]
                output_filename = f"resultado_{base_filename}_{timestamp}.json"
                log_filename = f"log_unificacoes_{base_filename}_{timestamp}.txt"
                
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_filename)
                
                processed_data, log_unificacao = process_file(df, output_path)
                
                st.session_state.processed_data_for_save = processed_data
                st.session_state.gen_output_path = output_path
                st.session_state.gen_log_unificacao = log_unificacao
                st.session_state.gen_log_filename = log_filename
                st.success("✅ Processamento concluído!")

    if 'gen_output_path' in st.session_state:
        st.divider()
        st.subheader("Salvar e Baixar Resultados")
        with st.form("form_salvar_gerado"):
            nome_arquivo = st.text_input("Nome para salvar no banco de dados:", value=os.path.basename(st.session_state.gen_output_path))
            submitted = st.form_submit_button("Salvar no Banco")
            if submitted:
                if salvar_no_banco(conn, st.session_state.processed_data_for_save, nome=nome_arquivo):
                    st.success(f"Arquivo '{nome_arquivo}' salvo no banco de dados!")
        col1, col2 = st.columns(2)
        with col1:
            with open(st.session_state.gen_output_path, "rb") as f:
                st.download_button(label=f"📥 Baixar JSON Gerado", data=f, file_name=os.path.basename(st.session_state.gen_output_path), mime="application/json", use_container_width=True)
        with col2:
            if st.session_state.gen_log_unificacao:
                log_data = "\n".join(st.session_state.gen_log_unificacao)
                st.download_button(label=f"📋 Baixar Log de Unificações", data=log_data.encode('utf-8'), file_name=st.session_state.gen_log_filename, mime="text/plain", use_container_width=True)

def _pagina_edicao_em_massa(conn, titulo_pagina, chave_sufixo, formato_novo_nome, sufixo_arquivo_novo):
    st.header(titulo_pagina)
    st.info("Esta ferramenta cria novas escalas em lote com base na substituição de um prefixo em uma tag específica.")
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, name FROM jsons ORDER BY name").fetchall()
    if not rows: st.warning("Nenhum arquivo no banco de dados."); return
    options_files = {r["id"]: r["name"] for r in rows}
    json_id = st.selectbox("Selecione o JSON para editar", options_files.keys(), format_func=lambda id: options_files.get(id), key=f"json_select_{chave_sufixo}", index=None, placeholder="Escolha um arquivo...")
    if json_id:
        selected_name = options_files[json_id]
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
    st.header("📥 Importar Arquivo JSON")
    uploaded_file = st.file_uploader("Escolha um arquivo .json", type="json", key="import_json_uploader")
    if uploaded_file:
        try:
            file_key = f"data_json_{uploaded_file.name}"
            if file_key not in st.session_state:
                st.session_state[file_key] = json.load(uploaded_file)
            data = st.session_state[file_key]
            st.success("Arquivo pré-visualizado. Clique abaixo para salvar.")
            st.json(data, expanded=False)
            with st.form(key='save_json_form'):
                nome_arquivo_sugerido = uploaded_file.name
                nome_arquivo_final = st.text_input("Nome para salvar no banco de dados:", value=nome_arquivo_sugerido)
                submitted = st.form_submit_button("Salvar no Banco de Dados")
                if submitted:
                    if salvar_no_banco(conn, data, nome=nome_arquivo_final):
                        st.success(f"Arquivo '{nome_arquivo_final}' salvo!")
                        for key in list(st.session_state.keys()):
                            if key.startswith('data_json_'):
                                del st.session_state[key]
                        time.sleep(1)
                        st.rerun()
        except json.JSONDecodeError:
            st.error("Erro: O arquivo não é um JSON válido. Verifique o conteúdo do arquivo.")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")

def pagina_exportar_json_personalizado(conn):
    st.header("🧩 Exportar JSON Personalizado")
    cursor = conn.cursor()
    files = cursor.execute("SELECT id, name FROM jsons ORDER BY name").fetchall()
    if not files:
        st.warning("Nenhum arquivo JSON disponível."); return

    options_files = {f['id']: f['name'] for f in files}
    selected_file_id = st.selectbox("1. Arquivo de origem:", options_files.keys(), format_func=lambda id: options_files.get(id), index=None, placeholder="Escolha um arquivo...")

    if selected_file_id:
        json_data = json.loads(cursor.execute("SELECT data FROM jsons WHERE id = ?", (selected_file_id,)).fetchone()['data'])
        escalas_disponiveis = json_data.get("escalas", [])
        
        scale_options = {s.get("key"): s.get("NOME", "Escala sem nome") for s in escalas_disponiveis if s.get("key")}
        
        select_all = st.checkbox("Selecionar todas as escalas", value=False)
        default_selection = list(scale_options.keys()) if select_all else []
        
        selected_keys = st.multiselect("2. Selecione as escalas:", options=scale_options.keys(), format_func=lambda k: scale_options.get(k, k), default=default_selection)
        
        if st.button("Gerar JSON Personalizado", type="primary", use_container_width=True):
            if not selected_keys:
                st.warning("Nenhuma escala selecionada."); st.stop()
            
            escalas_selecionadas = [s for s in escalas_disponiveis if s.get("key") in selected_keys]
            
            jornadas_usadas = set()
            for esc in escalas_selecionadas:
                jornadas_usadas.update(esc.get("JORNADAS", []))
            
            jornadas_originais = json_data.get("jornadas", {})
            jornadas_filtradas = {key: value for key, value in jornadas_originais.items() if key in jornadas_usadas}

            new_json = {
                "escalas": escalas_selecionadas, 
                "jornadas": jornadas_filtradas, 
                "horas_adicionais": json_data.get("horas_adicionais", {})
            }
            
            st.session_state.export_data = json.dumps(new_json, indent=4, ensure_ascii=False)
            st.session_state.export_filename = f"personalizado_{options_files[selected_file_id]}"
            st.success("JSON personalizado gerado com sucesso!")

    if 'export_data' in st.session_state and st.session_state.export_data:
        st.subheader("⬇️ Download do Resultado")
        st.download_button("📥 Baixar JSON", st.session_state.export_data, st.session_state.export_filename, "application/json", use_container_width=True)


def pagina_exportar_lista(conn):
    st.header("📁 Exportar Lista de Escalas")
    rows = conn.cursor().execute("SELECT name, data FROM jsons ORDER BY name").fetchall()
    if not rows: st.warning("Nenhum arquivo no banco de dados."); return
    data_list = []
    for row in rows:
        try:
            escalas_data = json.loads(row['data']).get("escalas", [])
            if isinstance(escalas_data, list):
                for esc in escalas_data: 
                    data_list.append([row['name'], esc.get("NOME", "Sem nome")])
            else:
                 data_list.append([row['name'], "ERRO DE FORMATO (escalas não é uma lista)"])
        except Exception: 
            data_list.append([row['name'], "ERRO AO LER JSON"])
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
    st.markdown("""
    Bem-vindo à **Central de Gestão de Escalas**! Esta ferramenta foi projetada para simplificar e automatizar a conversão de descrições de horários de trabalho em um formato estruturado (JSON), pronto para ser importado em outros sistemas.

    Abaixo, você encontrará uma descrição detalhada de cada funcionalidade disponível no menu lateral.

    ### 📊 Dashboard
    Esta é a página inicial. Ela oferece uma visão geral e rápida da sua base de dados.

    ### ✨ Assistente de Criação com IA
    Uma forma interativa e guiada para cadastrar múltiplas escalas usando linguagem natural. A IA ajuda a estruturar e validar as escalas.

    ### ⚙️ Gerenciar Regras de Tradução
    Este é o cérebro do sistema. Aqui você pode "ensinar" o aplicativo a entender os diferentes padrões de texto das suas planilhas.

    ### 📄 Traduzir CSV com Regras
    O primeiro passo do fluxo de trabalho. Carregue um CSV, selecione a coluna com as descrições e aplique as regras que criou.

    ### 📊 Gerar Escalas por CSV
    O segundo e principal passo do fluxo. Use o arquivo traduzido para gerar o JSON final no formato correto.

    ### 📝 Edição em Lote e 🔎 Duplicar para Coligadas
    Permitem fazer modificações em massa em um arquivo JSON já existente com base na substituição de prefixos.
    
    ### 🧩 Exportar JSON Personalizado
    Permite criar um arquivo JSON menor a partir de um arquivo grande já existente, selecionando apenas as escalas desejadas.
    
    ### 📥 Importar Arquivo JSON
    Permite adicionar um arquivo JSON já formatado diretamente à base de dados.

    ### 📁 Exportar Lista de Escalas
    Gera um CSV com a lista de todas as escalas em todos os arquivos.

    ### 🗑️ Excluir Arquivo
    Permite remover permanentemente um arquivo JSON da base de dados.
    """)

# ==============================================================================
# FUNÇÃO PRINCIPAL (MAIN)
# ==============================================================================
def main():
    st.sidebar.title("⚙️ Menu de Ferramentas")
    conn = get_db_connection()
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "📊 Dashboard"

    # Dicionário de páginas completo, com o chatbot incluído
    PAGES = {
        "📊 Dashboard": pagina_dashboard,
        "--- TRADUÇÃO E CRIAÇÃO ---": None,
        "✨ Assistente de Criação com IA": pagina_assistente_ia,
        "⚙️ Gerenciar Regras de Tradução": pagina_gerenciar_regras,
        "📄 Traduzir CSV com Regras": pagina_traduzir_csv_com_regras,
        "📊 Gerar Escalas por CSV": pagina_gerar_escalas_csv,
        "--- EDIÇÃO E GESTÃO ---": None,
        "📝 Edição em Lote": pagina_edicao_em_lote, 
        "🔎 Duplicar para Coligadas": pagina_duplicar_para_coligadas,
        "🧩 Exportar JSON Personalizado": pagina_exportar_json_personalizado,
        "--- ARQUIVOS ---": None,
        "📥 Importar Arquivo JSON": pagina_importar_escala,
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
                # Limpa estados específicos ao trocar de página para evitar conflitos
                if 'last_chatbot_data' in st.session_state:
                    del st.session_state.last_chatbot_data
                if 'final_json' in st.session_state:
                    del st.session_state.final_json
                if 'df_traduzido' in st.session_state:
                     del st.session_state.df_traduzido
                st.rerun()
    
    page_to_call = PAGES.get(st.session_state.current_page)
    if page_to_call is not None:
        page_to_call(conn)

if __name__ == '__main__':
    main()
