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

# =====================================================================================
# CONFIGURAÇÃO INICIAL E CONEXÃO COM BANCO DE DADOS
# =====================================================================================

# --- Configuração da Página (Deve ser o primeiro comando Streamlit) ---
st.set_page_config(page_title="Central de ADM Pessoal", layout="wide")

# --- Conexão com o Banco de Dados ---
# Usar @st.cache_resource garante que a conexão seja criada apenas uma vez.
@st.cache_resource
def get_db_connection():
    """Cria e gerencia a conexão com o banco de dados."""
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.isolation_level = None # Garante que as operações de escrita sejam salvas
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

def pagina_documentacao():
    st.header("📄 Documentação Recursos")
    st.write("Relatório técnico mostrando as dependências e módulos importados pela aplicação.")
    html_file_path = 'gestao de escalas.html'
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        with st.container(border=True):
            components.html(source_code, height=600, scrolling=True)
    except FileNotFoundError:
        st.error(f"Erro: O arquivo de documentação '{html_file_path}' não foi encontrado.")

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
                            nova_escala["key"] = fuzz.uuid4().hex
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
    st.sidebar.header("Opções de Exportação")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM jsons ORDER BY name")
    files = [row[0] for row in cursor.fetchall()]
    if not files:
        st.warning("Nenhum arquivo JSON disponível para exportação."); return
        
    selected_file = st.sidebar.selectbox("Arquivo de origem:", files, key="export_select")
    if selected_file:
        cursor.execute("SELECT data FROM jsons WHERE name = ?", (selected_file,))
        result = cursor.fetchone()
        if result:
            json_data = json.loads(result[0])
            scale_options = {scale.get("key"): scale.get("NOME") for scale in json_data.get("escalas", [])}
            selected_scales_keys = st.sidebar.multiselect("Selecione as escalas:", options=list(scale_options.keys()), format_func=lambda k: scale_options.get(k, k))
            if selected_scales_keys:
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
                            nova_escala["key"] = fuzz.uuid4().hex
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
    st.sidebar.header("Opções do Processador")
    uploaded_file = st.sidebar.file_uploader("Selecione .csv ou .xlsx", type=["csv", "xlsx"], key="csv_uploader")
    process_button = st.sidebar.button("🚀 Processar Escalas", disabled=(not uploaded_file))

    if process_button and uploaded_file:
        try:
            with st.spinner('Aguarde... Processando.'):
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)
                st.session_state.processed_df_head = df.head(10)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"resultado_{timestamp}.json"
                output_dir = "output"; os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_filename)
                process_file(df, output_path)
                st.session_state.output_path = output_path
            st.success("✅ Processamento concluído!")
        except Exception as e:
            st.error(f"❌ Erro ao processar o arquivo: {e}")
            if 'output_path' in st.session_state: del st.session_state.output_path
            
    if 'processed_df_head' in st.session_state:
        st.subheader("📄 Pré-visualização do Arquivo de Entrada")
        st.dataframe(st.session_state.processed_df_head)
    if 'output_path' in st.session_state:
        st.subheader("⬇️ Download do Resultado")
        try:
            with open(st.session_state.output_path, "rb") as f:
                st.download_button(label=f"📥 Baixar {os.path.basename(st.session_state.output_path)}", data=f, file_name=os.path.basename(st.session_state.output_path), mime="application/json")
            with st.expander("Visualizar JSON Gerado"):
                with open(st.session_state.output_path, "r", encoding="utf-8") as f: st.json(f.read())
        except FileNotFoundError: st.error("Arquivo de resultado não foi encontrado.")

def pagina_excluir_arquivo():
    st.header("🗑️ Excluir Arquivo")
    st.sidebar.header("Opções de Exclusão")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM jsons ORDER BY name")
    files_to_delete = [row[0] for row in cursor.fetchall()]
    if not files_to_delete:
        st.warning("Nenhum arquivo para excluir."); return
    file_to_delete = st.sidebar.selectbox("Arquivo para excluir:", files_to_delete, index=None, placeholder="Selecione...")
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

# =====================================================================================
# LÓGICA PRINCIPAL DA APLICAÇÃO (MENU E ROTEAMENTO)
# =====================================================================================

def main():
    """Função principal que organiza a UI e o roteamento."""
    st.sidebar.title("⚙️ Menu")

    # Mapeia os nomes do menu para as funções de página correspondentes
    PAGES = {
        "📄 Documentação Recursos": pagina_documentacao,
        "📥 Importar Escala": pagina_importar_escala,
        "📝 Edição em Lote": pagina_edicao_em_lote,
        "🧩 Exportar JSON Personalizado": pagina_exportar_json_personalizado,
        "🔎 Duplicar para coligadas/filiais": pagina_duplicar_para_coligadas,
        "📊 Gerar escalas através de CSV": pagina_gerar_escalas_csv,
        "🗑️ Excluir Arquivo": pagina_excluir_arquivo,
        "📁 Exportar Lista de Arquivos e Escalas": pagina_exportar_lista,
    }

    # Inicializa o estado da página, se não existir
    if 'page' not in st.session_state:
        st.session_state.page = "📄 Documentação Recursos"

    # Cria os botões do menu na sidebar
    for page_name in PAGES.keys():
        if st.sidebar.button(page_name, use_container_width=True, key=f"btn_{page_name}"):
            # Se o botão for clicado, atualiza a página no estado da sessão
            if st.session_state.page != page_name:
                st.session_state.page = page_name
                st.rerun() # Força o recarregamento da página

    # Chama a função da página atualmente selecionada
    page_function = PAGES[st.session_state.page]
    page_function()

if __name__ == "__main__":
    main()
