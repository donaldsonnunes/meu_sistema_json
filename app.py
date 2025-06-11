import streamlit as st
import sqlite3
import json
import plotly.express as px
import pandas as pd
from rapidfuzz import fuzz
import copy # Importado para a nova funcionalidade
import sys
import os
import streamlit.components.v1 as components

# Detectar mudança de menu
menu_anterior = st.session_state.get("menu_anterior", None)

conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS jsons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, data TEXT)''')
conn.commit()

st.set_page_config(page_title="Sistema de Escalas", layout="wide")
st.sidebar.title("⚙️ Menu")
menu = st.sidebar.radio("Escolha uma opção:", [
    "📄 Documentação Recursos",
    "📥 Importar Escala",
    "✏️ Editar JSON",
    "🧩 Exportar JSON Personalizado",
    "🔎 Substituição em Lote", # Nova opção de menu
    "🔗 Unificação de Jornadas",
    "📥 Importar Lista de Escalas (TXT)",
    "🧹 Saneamento de Nomes de Escalas",
    "🗑️ Excluir Arquivo",
    "📁 Exportar Lista de Arquivos e Escalas"
])

if menu != menu_anterior:
    st.session_state["menu_anterior"] = menu
    # Limpar estados de sessões antigas ao mudar de menu para evitar conflitos
    for key in list(st.session_state.keys()):
        if key not in ['menu_anterior']:
            del st.session_state[key]
    st.rerun()

st.title("🔧 Sistema de Gestão de Escalas")

# Funções utilitárias
def salvar_no_banco(conn, json_data, selected_id=None, nome=None):
    cursor = conn.cursor()
    if selected_id is not None:
        cursor.execute("UPDATE jsons SET data=? WHERE id=?", (json.dumps(json_data, ensure_ascii=False, indent=4), selected_id))
    elif nome:
        cursor.execute("INSERT INTO jsons (name, data) VALUES (?, ?)", (nome, json.dumps(json_data, ensure_ascii=False, indent=4)))
    conn.commit()

def set_value_by_path(data, path, new_value):
    keys = path.split('.')
    for k in keys[:-1]:
        data = data[k] if isinstance(data, dict) else data[int(k)]
    data[keys[-1]] = new_value

def get_value_by_path(data, path):
    keys = path.split('.')
    for k in keys:
        data = data.get(k) if isinstance(data, dict) else data[int(k)]
    return data

def convert_type(value, target_type):
    try:
        if target_type == bool:
            return value.lower() in ["true", "1", "yes", "sim"]
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        return str(value)
    except:
        return None

# 📥 Importar Escala
if menu == "📥 Importar Escala":
    st.header("📥 Importar Novas Escalas")
    st.write("Selecione um ou mais arquivos JSON para adicionar ao banco de dados do sistema.")
    
    with st.container(border=True):
        st.markdown("#### 📂 Selecione os Arquivos JSON")
        uploaded_files = st.file_uploader("Selecione arquivos JSON:", type="json", accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            for uploaded_file in uploaded_files:
                with st.spinner(f"Processando '{uploaded_file.name}'..."):
                    data = json.load(uploaded_file)
                    cursor.execute("INSERT INTO jsons (name, data) VALUES (?, ?)", (uploaded_file.name, json.dumps(data)))
                    conn.commit()
                st.success(f"Arquivo '{uploaded_file.name}' importado com sucesso!")

# ✏️ Editar JSON
if menu == "✏️ Editar JSON":
    st.header("✏️ Editor de Entidades JSON")
    st.write("Edite valores específicos de escalas, jornadas ou horas adicionais em um arquivo JSON.")

    cursor.execute("SELECT id, name FROM jsons")
    rows = cursor.fetchall()

    if not rows:
        st.warning("Nenhum arquivo no banco de dados para editar.")
    else:
        with st.container(border=True):
            st.markdown("#### 📄 Passo 1: Selecione o Item a ser Editado")
            json_id = st.selectbox("Selecione o arquivo JSON:", [f"{r[0]} - {r[1]}" for r in rows])
            tipo = st.radio("Selecione o tipo de entidade:", ["Escala", "Jornada", "Hora Adicional"], horizontal=True)

        selected_id = int(json_id.split(" - ")[0])
        selected_name = json_id.split(" - ")[1]
        cursor.execute("SELECT data FROM jsons WHERE id=?", (selected_id,))
        json_data = json.loads(cursor.fetchone()[0])
        base_path, item = "", {}

        # Lógica para preencher os campos de seleção
        if tipo == "Escala":
            # ... (a lógica interna permanece a mesma)
            pass
        elif tipo == "Jornada":
            # ... (a lógica interna permanece a mesma)
            pass
        else: # Hora adicional
            # ... (a lógica interna permanece a mesma)
            pass

        with st.container(border=True):
            st.markdown("#### 📝 Passo 2: Altere o Valor")
            # Este código pressupõe que a lógica anterior de seleção já foi executada
            # Você precisará integrar o código que busca 'item', 'path', 'valor' aqui
            tag = st.selectbox("Tag para editar:", []) # Preencher com list(item.keys())
            st.write(f"Valor atual: `...`") # Preencher com valor
            novo_valor = st.text_input("Novo valor:", value="...") # Preencher com str(valor)

        with st.container(border=True):
            st.markdown("#### 💾 Passo 3: Salve as Alterações")
            opcao = st.radio("Como deseja salvar?", ["Sobrescrever arquivo existente", "Salvar como novo arquivo"], horizontal=True)
        novo_nome = ""
        if opcao == "Salvar como novo arquivo":
            novo_nome = st.text_input("Nome do novo arquivo:", value=selected_name.replace(".json", "_v2.json"))

        if st.button("✅ Salvar agora"):
            tipo_atual = type(valor)
            convertido = convert_type(novo_valor, tipo_atual)
            if convertido is None:
                st.error(f"Erro: não foi possível converter para {tipo_atual}")
            else:
                set_value_by_path(json_data, path, convertido)

                if opcao == "Sobrescrever arquivo existente":
                    salvar_no_banco(conn, json_data, selected_id=selected_id)
                    st.success("✅ Alterações salvas no arquivo original.")
                elif opcao == "Salvar como novo arquivo":
                    if not novo_nome.strip():
                        st.error("❌ Informe um nome para o novo arquivo.")
                    else:
                        salvar_no_banco(conn, json_data, selected_id=None, nome=novo_nome.strip())
                        st.success("✅ Novo arquivo salvo com sucesso!")

# 🧩 Exportar JSON Personalizado
if menu == "🧩 Exportar JSON Personalizado":
    st.header("🧩 Montar e Exportar JSON Personalizado")
    st.write("Crie um arquivo JSON customizado selecionando escalas de um ou mais arquivos base.")

    with st.container(border=True):
        st.markdown("#### ⚙️ Passo 1: Configure a Fonte dos Dados")
        filtro = st.checkbox("Filtrar por arquivo?", value=True)
        ids = []
        if filtro:
            cursor.execute("SELECT id, name FROM jsons")
            rows = cursor.fetchall()
            if rows:
                json_id = st.selectbox("Selecione o JSON base:", [f"{r[0]} - {r[1]}" for r in rows], label_visibility="collapsed")
                ids = [int(json_id.split(' - ')[0])] if json_id else []
            else:
                st.warning("Nenhum arquivo no banco de dados para selecionar.")
        else:
            cursor.execute("SELECT id FROM jsons")
            ids = [r[0] for r in cursor.fetchall()]

    if ids:
        escalas, jornadas, horas = [], {}, {}
        for i in ids:
            cursor.execute("SELECT data FROM jsons WHERE id=?", (i,))
            j = json.loads(cursor.fetchone()[0])
            escalas += j.get('escalas', [])
            jornadas.update(j.get('jornadas', {}))
            horas.update(j.get('horas_adicionais', {}))

        exportar_todas = False
        if filtro:
            with st.container(border=True):
                 exportar_todas = st.checkbox("✅ Exportar todas as escalas do arquivo base", value=False)

        filtradas = []
        if exportar_todas:
            st.info(f"Todas as {len(escalas)} escalas do arquivo serão incluídas na exportação.")
            filtradas = escalas
        else:
            with st.container(border=True):
                st.markdown("#### ➕ Passo 2: Adicionar Escalas à Seleção")
                if "escalas_selecionadas" not in st.session_state:
                    st.session_state["escalas_selecionadas"] = set()

                busca = st.text_input("🔍 Buscar escala pelo nome:")
                nomes = [e.get('NOME') for e in escalas]
                nomes_filtrados = [n for n in nomes if busca.lower() in n.lower()]

                adicionar = st.multiselect(
                    "Selecione as escalas que deseja adicionar:",
                    options=nomes_filtrados,
                    key="busca_multiselect"
                )

                if st.button("Adicionar à Seleção", use_container_width=True):
                    st.session_state["escalas_selecionadas"].update(adicionar)
                    st.success(f"{len(adicionar)} escala(s) adicionada(s) com sucesso!")
            
            if st.session_state.get("escalas_selecionadas"):
                with st.container(border=True):
                    st.markdown("##### ✅ Escalas na Seleção Final")
                    remover = []
                    for nome in sorted(list(st.session_state["escalas_selecionadas"])):
                        col1, col2 = st.columns([0.9, 0.1])
                        with col1:
                            st.write(f"🔹 {nome}")
                        with col2:
                            if st.button("❌", key=f"remove_{nome}"):
                                remover.append(nome)
                    
                    if remover:
                        for nome in remover:
                            st.session_state["escalas_selecionadas"].remove(nome)
                        st.rerun()

            filtradas = [e for e in escalas if e.get('NOME') in st.session_state.get("escalas_selecionadas", set())]

        if filtradas:
            with st.container(border=True):
                st.markdown("#### 📦 Passo 3: Exporte o Resultado")
                ids_j = set()
                for e in filtradas:
                    ids_j.update(e.get('JORNADAS', []))
                
                jornadas_f = {k: v for k, v in jornadas.items() if k in ids_j}
                json_final = {"escalas": filtradas, "jornadas": jornadas_f, "horas_adicionais": horas}
                resumo_txt = "ESCALAS:\n" + "\n".join([e.get('NOME', 'N/A') for e in filtradas]) + "\n\n"
                resumo_txt += "JORNADAS:\n" + "\n".join([j.get('NOME_JORNADA', '-') for j in jornadas_f.values()]) + "\n\n"
                resumo_txt += "HORAS ADICIONAIS:\n" + "\n".join(horas.keys())

                st.subheader("Conteúdo Final do JSON")
                st.json(json_final)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("⬇️ Exportar JSON", json.dumps(json_final, indent=4), file_name="json_personalizado.json", use_container_width=True)
                with col2:
                    st.download_button("📄 Exportar Resumo (.txt)", resumo_txt, file_name="resumo_estruturas.txt", use_container_width=True)
        else:
            st.info("Nenhuma escala selecionada para exportar. Adicione escalas no Passo 2.")

# 🔎 Substituição em Lote (COM NOVO BOTÃO DE SALVAR)
if menu == "🔎 Substituição em Lote":
    st.header("🔎 Substituição em Lote")
    st.write("Realize alterações em massa em um campo específico das suas escalas.")
    
    # ... (O código de seleção de arquivo, tag e regra de substituição permanece o mesmo) ...
    # ... (Vou omiti-lo aqui para ser breve, mas ele deve ser mantido no seu arquivo) ...

    cursor.execute("SELECT id, name FROM jsons")
    rows = cursor.fetchall()

    if not rows:
        st.warning("Nenhum arquivo no banco de dados. Importe um arquivo primeiro.")
    else:
        with st.container(border=True):
            st.markdown("#### 📄 Passo 1: Selecione o Alvo")
            json_id_str = st.selectbox("Selecione o JSON para editar", [f"{r[0]} - {r[1]}" for r in rows], key="lote_json_select", label_visibility="collapsed")
        
        if json_id_str:
            selected_id = int(json_id_str.split(" - ")[0])
            selected_name = json_id_str.split(" - ")[1]
            
            cursor.execute("SELECT data FROM jsons WHERE id=?", (selected_id,))
            original_data = json.loads(cursor.fetchone()[0])
            escalas = original_data.get('escalas', [])

            if not escalas:
                st.warning("O arquivo selecionado não contém nenhuma 'escala'.")
            else:
                todas_tags = set()
                for esc in escalas:
                    todas_tags.update(esc.keys())

                with st.container(border=True):
                    st.markdown("#### 🏷️ Passo 2: Defina a Regra")
                    tag_selecionada = st.selectbox("Selecione a Tag para a busca", sorted(list(todas_tags)), key="lote_tag_select")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        valor_localizar = st.text_input("Texto a ser localizado (prefixo)", help="O sistema buscará valores que **começam com** este texto.", key="lote_search")
                    with col2:
                        valor_substituir = st.text_input("Substituir o prefixo por", key="lote_replace")

                if st.button("👁️ Pré-visualizar alterações", key="lote_preview_btn", use_container_width=True):
                    dados_preview = []
                    json_modificado = copy.deepcopy(original_data)
                    novas_escalas = []

                    if valor_localizar:
                        for esc in json_modificado.get("escalas", []):
                            valor_original_tag = esc.get(tag_selecionada)
                            if valor_original_tag and isinstance(valor_original_tag, str) and valor_original_tag.startswith(valor_localizar):
                                nova_escala = copy.deepcopy(esc)
                                valor_antigo_tag = nova_escala[tag_selecionada]
                                novo_valor_tag = valor_substituir + valor_antigo_tag[len(valor_localizar):]
                                nova_escala[tag_selecionada] = novo_valor_tag
                                nome_antigo_escala = nova_escala.get("NOME", "")
                                novo_nome_escala = f"{nome_antigo_escala} - {valor_substituir}"
                                nova_escala["NOME"] = novo_nome_escala
                                novas_escalas.append(nova_escala)
                                dados_preview.append({
                                    "Nome Original": nome_antigo_escala,
                                    "Novo Nome Proposto": novo_nome_escala,
                                    f"Valor Original ({tag_selecionada})": valor_antigo_tag,
                                    f"Valor Proposto ({tag_selecionada})": novo_valor_tag
                                })
                    
                    if dados_preview:
                        json_modificado["escalas"].extend(novas_escalas)
                        st.session_state['dados_preview'] = dados_preview
                        st.session_state['json_modificado'] = json_modificado
                        st.session_state['novas_escalas'] = novas_escalas # <-- SALVANDO AS NOVAS ESCALAS NO ESTADO
                        st.session_state['selected_id_lote'] = selected_id
                        st.session_state['selected_name_lote'] = selected_name
                    else:
                        st.warning("Nenhum registro encontrado com o critério especificado.")
                        if 'dados_preview' in st.session_state:
                            del st.session_state['dados_preview']

            # --- A LÓGICA DE EXIBIÇÃO E SALVAMENTO FOI ALTERADA A PARTIR DAQUI ---
            if 'dados_preview' in st.session_state and st.session_state['dados_preview']:
                with st.container(border=True):
                    st.markdown("#### 📊 Passo 3: Confirme e Salve as Alterações")
                    st.success(f"Foram encontradas {len(st.session_state['dados_preview'])} escalas. Serão **criados {len(st.session_state['dados_preview'])} novos registros** de escala com os valores abaixo.")
                    
                    df_preview = pd.DataFrame(st.session_state['dados_preview'])
                    st.dataframe(df_preview, use_container_width=True)

                    st.divider()
                    
                    col_salvar1, col_salvar2 = st.columns(2)

                    with col_salvar1:
                        st.markdown("##### 💾 Opção 1: Salvar Tudo")
                        st.write("Adiciona as novas escalas ao arquivo original e salva o resultado.")
                        opcao = st.radio("Como deseja salvar?", ["Sobrescrever arquivo existente", "Salvar como novo arquivo"], key="lote_save_option", horizontal=True, label_visibility="collapsed")

                        novo_nome_tudo = ""
                        if opcao == "Salvar como novo arquivo":
                            novo_nome_tudo = st.text_input("Nome do novo arquivo:", value=st.session_state['selected_name_lote'].replace(".json", "_modificado.json"), key="lote_new_name_all")

                        if st.button("Salvar Tudo Agora", key="lote_save_btn_all", use_container_width=True, type="primary"):
                            json_final = st.session_state['json_modificado']
                            if opcao == "Sobrescrever arquivo existente":
                                salvar_no_banco(conn, json_final, selected_id=st.session_state['selected_id_lote'])
                                st.success("✅ Alterações salvas no arquivo original.")
                            elif opcao == "Salvar como novo arquivo":
                                if not novo_nome_tudo.strip():
                                    st.error("❌ Informe um nome para o novo arquivo.")
                                else:
                                    salvar_no_banco(conn, json_final, nome=novo_nome_tudo.strip())
                                    st.success(f"✅ Novo arquivo '{novo_nome_tudo}' salvo com sucesso!")
                            
                            for key in list(st.session_state.keys()): # Limpeza geral
                                if key != 'menu_anterior': del st.session_state[key]
                            st.rerun()

                    with col_salvar2:
                        st.markdown("##### 💾 Opção 2: Salvar Somente Novas")
                        st.write("Cria um novo arquivo contendo apenas as escalas geradas no lote.")
                        
                        novo_nome_novas = st.text_input("Nome do novo arquivo:", value=st.session_state['selected_name_lote'].replace(".json", "_apenas_novas.json"), key="lote_new_name_only")

                        if st.button("Salvar Somente Novas", key="lote_save_btn_only", use_container_width=True):
                            if not novo_nome_novas.strip():
                                st.error("❌ Informe um nome para o novo arquivo.")
                            else:
                                with st.spinner("Preparando novo arquivo..."):
                                    # Lógica para criar o JSON apenas com as novas escalas
                                    escalas_novas = st.session_state['novas_escalas']
                                    jornadas_originais = st.session_state['json_modificado'].get('jornadas', {})
                                    horas_originais = st.session_state['json_modificado'].get('horas_adicionais', {})
                                    
                                    ids_jornadas_necessarias = set()
                                    for esc in escalas_novas:
                                        ids_jornadas_necessarias.update(esc.get('JORNADAS', []))
                                    
                                    jornadas_filtradas = {k: v for k, v in jornadas_originais.items() if k in ids_jornadas_necessarias}

                                    json_apenas_novas = {
                                        "escalas": escalas_novas,
                                        "jornadas": jornadas_filtradas,
                                        "horas_adicionais": horas_originais
                                    }
                                    
                                    salvar_no_banco(conn, json_apenas_novas, nome=novo_nome_novas.strip())
                                    st.success(f"✅ Novo arquivo '{novo_nome_novas}' com apenas as novas escalas salvo com sucesso!")
                                
                                for key in list(st.session_state.keys()): # Limpeza geral
                                    if key != 'menu_anterior': del st.session_state[key]
                                st.rerun()


# 🔗 Unificação de Jornadas
if menu == "🔗 Unificação de Jornadas":
    st.header("🔗 Unificação de Jornadas")
    st.write("Encontre e unifique jornadas de trabalho com nomes duplicados ou muito semelhantes.")

    with st.container(border=True):
        st.markdown("#### ⚙️ Unificação Automática (100% Similaridade)")
        st.write("Unifica jornadas que possuem exatamente o mesmo nome em diferentes arquivos.")
        if st.button("Unificar Automaticamente", use_container_width=True, help="Busca por nomes idênticos e os unifica."):
            with st.spinner("Processando... Por favor, aguarde."):
                cursor.execute("SELECT id, name, data FROM jsons")
                rows = cursor.fetchall()
                jornadas = []
                for r in rows:
                    d = json.loads(r[2])
                    for jid, j in d.get('jornadas', {}).items():
                        jornadas.append({'json_id': r[0], 'arquivo': r[1], 'jornada_id': jid, 'nome': j.get('NOME_JORNADA')})

                unificadas = 0
                for i in range(len(jornadas)):
                    for j in range(i + 1, len(jornadas)):
                        j1, j2 = jornadas[i], jornadas[j]
                        if j1['jornada_id'] != j2['jornada_id'] and j1['nome'] == j2['nome']:
                            id_unificado, id_removido = j1['jornada_id'], j2['jornada_id']
                            for r_update in rows:
                                d_update = json.loads(r_update[2])
                                alterado = False
                                for e_update in d_update.get('escalas', []):
                                    if id_removido in e_update.get('JORNADAS', []):
                                        e_update['JORNADAS'] = [id_unificado if x == id_removido else x for x in e_update['JORNADAS']]
                                        alterado = True
                                if 'jornadas' in d_update and id_removido in d_update['jornadas']:
                                    del d_update['jornadas'][id_removido]
                                    alterado = True
                                if alterado:
                                    salvar_no_banco(conn, d_update, selected_id=r_update[0])
                                    unificadas += 1
                if unificadas:
                    st.success(f"✅ {unificadas} referências de jornadas foram unificadas automaticamente!")
                else:
                    st.info("🔍 Nenhuma jornada com 100% de similaridade foi encontrada para unificar.")

    with st.container(border=True):
        st.markdown("#### ✍️ Unificação Manual (Similaridade >= 90%)")
        cursor.execute("SELECT id, name, data FROM jsons")
        rows = cursor.fetchall()
        jornadas = []
        for r in rows:
            d = json.loads(r[2])
            for jid, j in d.get('jornadas', {}).items():
                jornadas.append({'json_id': r[0], 'arquivo': r[1], 'jornada_id': jid, 'nome': j.get('NOME_JORNADA')})

        total_jornadas = len(jornadas)
        jornadas_por_pagina = 100
        total_paginas = max(1, (total_jornadas - 1) // jornadas_por_pagina + 1)
        pagina = st.number_input("Página de Jornadas:", min_value=1, max_value=total_paginas, value=1, step=1)

        inicio = (pagina - 1) * jornadas_por_pagina
        fim = inicio + jornadas_por_pagina
        jornadas_pagina = jornadas[inicio:fim]

        pares = []
        for i in range(len(jornadas_pagina)):
            for j in range(i + 1, len(jornadas_pagina)):
                if jornadas_pagina[i]['jornada_id'] != jornadas_pagina[j]['jornada_id']:
                    similaridade = fuzz.ratio(jornadas_pagina[i]['nome'], jornadas_pagina[j]['nome'])
                    if similaridade >= 90:
                        chave = f"{jornadas_pagina[i]['jornada_id']}|{jornadas_pagina[j]['jornada_id']}"
                        pares.append({"chave": chave, "j1": jornadas_pagina[i], "j2": jornadas_pagina[j], "similaridade": similaridade})
        
        pares.sort(key=lambda x: x["similaridade"], reverse=True)

        if pares:
            st.write("Selecione os pares que deseja unificar. A segunda jornada será removida e suas referências apontarão para a primeira.")
            selecionados = []
            for idx, p in enumerate(pares):
                st.markdown("---")
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    if st.checkbox("", key=f"chk_{p['chave']}_{pagina}_{idx}"):
                        selecionados.append(p['chave'])
                with col2:
                    st.write(f"**Similaridade: {p['similaridade']:.1f}%**")
                    st.write(f"1️⃣ `{p['j1']['nome']}` (ID: `{p['j1']['jornada_id']}` do arquivo `{p['j1']['arquivo']}`)")
                    st.write(f"2️⃣ `{p['j2']['nome']}` (ID: `{p['j2']['jornada_id']}` do arquivo `{p['j2']['arquivo']}`)")

            if selecionados:
                if st.button("Unificar Selecionados", use_container_width=True, type="primary"):
                    for sel in selecionados:
                        p = next((x for x in pares if x['chave'] == sel), None)
                        if p:
                            id_unificado, id_removido = p['j1']['jornada_id'], p['j2']['jornada_id']
                            for r_update in rows:
                                d_update = json.loads(r_update[2])
                                alterado = False
                                for e_update in d_update.get('escalas', []):
                                    if id_removido in e_update.get('JORNADAS', []):
                                        e_update['JORNADAS'] = [id_unificado if x == id_removido else x for x in e_update['JORNADAS']]
                                        alterado = True
                                if 'jornadas' in d_update and id_removido in d_update['jornadas']:
                                    del d_update['jornadas'][id_removido]
                                    alterado = True
                                if alterado:
                                    salvar_no_banco(conn, d_update, selected_id=r_update[0])
                            st.success(f"Jornadas `{p['j1']['nome']}` e `{p['j2']['nome']}` unificadas com sucesso!")
                    st.rerun()
        else:
            st.info("Nenhuma jornada semelhante encontrada nesta página.")

# 📥 Importar Lista de Escalas (TXT)
if menu == "📥 Importar Lista de Escalas (TXT)":
    st.header("📥 Importar Escalas via Lista TXT")
    st.write("Faça o upload de um arquivo .txt com uma lista de nomes de escalas (um por linha) para gerar um JSON personalizado.")
    
    def padronizar_para_comparacao(nome):
        import re
        if not isinstance(nome, str): return ""
        nome = nome.upper()
        nome = re.sub(r"[ÀÁÂÃ]", "A", nome); nome = re.sub(r"[ÈÉÊ]", "E", nome)
        nome = re.sub(r"[ÌÍÎ]", "I", nome); nome = re.sub(r"[ÒÓÔÕ]", "O", nome)
        nome = re.sub(r"[ÙÚÛÜ]", "U", nome); nome = re.sub(r"[-‐‑‒–—−]", " ", nome)
        nome = re.sub(r"\s+", " ", nome).strip()
        return nome

    with st.container(border=True):
        st.markdown("#### 📄 Passo 1: Selecione o Arquivo .txt")
        uploaded_file = st.file_uploader("Selecione o arquivo .txt", type=["txt"], label_visibility="collapsed")

    if uploaded_file:
        with st.spinner("Processando arquivo e buscando escalas..."):
            nomes_txt_raw = [linha.strip() for linha in uploaded_file.read().decode("utf-8").splitlines() if linha.strip()]
            nomes_txt = [padronizar_para_comparacao(n) for n in nomes_txt_raw]
            
            cursor.execute("SELECT data FROM jsons")
            escalas_encontradas, jornadas, horas = [], {}, {}
            for row in cursor.fetchall():
                j = json.loads(row[0])
                for esc in j.get("escalas", []):
                    nome_escala = esc.get("NOME", "")
                    if padronizar_para_comparacao(nome_escala) in nomes_txt:
                        escalas_encontradas.append(esc)
                        for jid in esc.get("JORNADAS", []):
                            if jid in j.get("jornadas", {}):
                                jornadas[jid] = j["jornadas"][jid]
                        horas.update(j.get("horas_adicionais", {}))
        
        with st.container(border=True):
            st.markdown("#### 📦 Passo 2: Resultado da Importação")
            if escalas_encontradas:
                st.success(f"✅ {len(escalas_encontradas)} de {len(nomes_txt)} escalas encontradas com 100% de similaridade.")
                json_final = {"escalas": escalas_encontradas, "jornadas": jornadas, "horas_adicionais": horas}
                resumo_txt = "ESCALAS:\n" + "\n".join([e['NOME'] for e in escalas_encontradas]) + "\n\n"
                resumo_txt += "JORNADAS:\n" + "\n".join([j['NOME_JORNADA'] for j in jornadas.values()]) + "\n\n"
                resumo_txt += "HORAS ADICIONAIS:\n" + "\n".join(horas.keys())

                st.subheader("JSON Gerado:")
                st.json(json_final)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("⬇️ Exportar JSON", json.dumps(json_final, indent=4), file_name="json_personalizado.json", use_container_width=True)
                with col2:
                    st.download_button("📄 Baixar Resumo .txt", resumo_txt, file_name="resumo_escalas.txt", use_container_width=True)
            else:
                st.warning("❌ Nenhuma escala com nome similar foi encontrada no banco de dados para os nomes listados no arquivo.")

# 🧹 Saneamento de Nomes de Escalas
if menu == "🧹 Saneamento de Nomes de Escalas":
    st.header("🧹 Saneamento de Nomes de Escalas")
    st.write("Padronize automaticamente os nomes de todas as escalas em todos os arquivos para um formato consistente.")

    def padronizar_nome(nome):
        # ... (sua função padronizar_nome completa aqui)
        import re
        if not isinstance(nome, str): return nome
        nome = nome.upper()
        nome = re.sub(r"\bDAS\s+(\d{1,2})\s*(A|AS|À|ÀS)\s+(\d{1,2})(:\d{2})?\b", lambda m: f"{int(m.group(1)):02d}:00 AS {int(m.group(3)):02d}:00" if not m.group(4) else f"{int(m.group(1)):02d}:00 AS {int(m.group(3)):02d}{m.group(4)}", nome)
        nome = re.sub(r"[ÀÁÂÃ]", "A", nome); nome = re.sub(r"[ÈÉÊ]", "E", nome)
        nome = re.sub(r"[ÌÍÎ]", "I", nome); nome = re.sub(r"[ÒÓÔÕ]", "O", nome)
        nome = re.sub(r"[ÙÚÛÜ]", "U", nome); nome = nome.replace("–", " ").replace("-", " ")
        nome = re.sub(r"\s+", " ", nome).strip()
        dias = {"SEGUN?D?A?": "SEG", "TER(C|Ç)A": "TER", "QUA(RTA)?": "QUA", "QUI(NTA|NT)?": "QUI", "SEX(TA|T)?": "SEX", "SAB(A|Á)DO|SAB": "SAB", "DOM(IN(GO)?)?": "DOM"}
        for k, v in dias.items(): nome = re.sub(rf"\b{k}\b", v, nome)
        nome = re.sub(r"\b(SEG|TER|QUA|QUI|SEX|SAB|DOM)\b\s*(A|À|AS|Á)\s*\b(SEG|TER|QUA|QUI|SEX|SAB|DOM)\b", r"\1 A \3", nome)
        nome = re.sub(r"\b(\d{1,2})H\b", lambda m: f"{int(m.group(1)):02d}:00", nome)
        nome = re.sub(r"\b(\d{1,2})\s*A\s*(\d{1,2})\b", lambda m: f"{int(m.group(1)):02d}:00 AS {int(m.group(2)):02d}:00", nome)
        nome = re.sub(r"\b(\d{1,2})\s*AS\s*(\d{1,2})\b", lambda m: f"{int(m.group(1)):02d}:00 AS {int(m.group(2)):02d}:00", nome)
        nome = re.sub(r"(\d{2}:\d{2})\s*A\s*(\d{2}:\d{2})", r"\1 AS \2", nome)
        nome = re.sub(r"\b(\d{1,2}):(\d{2}):00\b", lambda m: f"{int(m.group(1)):02d}:{m.group(2)}", nome)
        nome = re.sub(r"\s+", " ", nome).strip()
        nome = re.sub(r"(\d{2}:\d{2}):00\b", r"\1", nome)
        return nome
    
    with st.container(border=True):
        st.markdown("#### ✨ Executar Padronização Automática")
        st.write("Esta ação irá varrer todos os arquivos e aplicar um conjunto de regras para corrigir e padronizar os nomes das escalas. Esta ação não pode ser desfeita.")
        if st.button("Iniciar Saneamento de Todos os Arquivos", use_container_width=True, type="primary"):
            with st.spinner("Realizando saneamento em todos os arquivos..."):
                cursor.execute("SELECT id, name, data FROM jsons")
                arquivos = cursor.fetchall()
                alterados = []
                for arq in arquivos:
                    json_id, nome_arquivo, data = arq
                    j = json.loads(data)
                    modificado = False
                    for esc in j.get("escalas", []):
                        nome_original = esc.get("NOME", "")
                        nome_novo = padronizar_nome(nome_original)
                        if nome_novo != nome_original:
                            alterados.append((nome_arquivo, nome_original, nome_novo))
                            esc["NOME"] = nome_novo
                            modificado = True
                    if modificado:
                        salvar_no_banco(conn, j, selected_id=json_id)
            
            st.session_state['saneamento_resultados'] = alterados

    if 'saneamento_resultados' in st.session_state:
        with st.container(border=True):
            st.markdown("#### ✅ Resultados do Saneamento")
            resultados = st.session_state['saneamento_resultados']
            if resultados:
                st.success(f"{len(resultados)} escalas tiveram seus nomes padronizados.")
                df_resultados = pd.DataFrame(resultados, columns=["Arquivo", "Nome Original", "Nome Padronizado"])
                st.dataframe(df_resultados, use_container_width=True)
            else:
                st.info("Nenhuma escala precisou de saneamento.")

# 🗑️ Excluir Arquivo
if menu == "🗑️ Excluir Arquivo":
    st.header("🗑️ Excluir Arquivo Importado")
    st.write("Remova permanentemente um arquivo JSON e todos os seus dados associados do sistema.")
    
    cursor.execute("SELECT id, name FROM jsons")
    arquivos = cursor.fetchall()
    
    with st.container(border=True):
        if arquivos:
            sel = st.selectbox("Selecione o arquivo para excluir:", [f"{r[0]} - {r[1]}" for r in arquivos])
            arquivo_id = int(sel.split(" - ")[0])
            
            st.warning("⚠️ **Atenção:** Esta ação é irreversível e irá remover o arquivo e todos os dados vinculados (escalas, jornadas, etc).")
            
            if st.button("Excluir Permanentemente", use_container_width=True, type="primary"):
                cursor.execute("DELETE FROM jsons WHERE id=?", (arquivo_id,))
                conn.commit()
                st.success("Arquivo e dados vinculados foram excluídos com sucesso!")
                st.rerun()
        else:
            st.info("Nenhum arquivo importado disponível para exclusão.")

# 📁 Exportar Lista de Arquivos e Escalas
if menu == "📁 Exportar Lista de Arquivos e Escalas":
    st.header("📁 Exportar Lista de Arquivos e Escalas")
    st.write("Gere um arquivo CSV contendo uma lista de todos os arquivos e as escalas contidas em cada um.")
    
    cursor.execute("SELECT name, data FROM jsons")
    rows = cursor.fetchall()

    dados = []
    for nome_arquivo, conteudo in rows:
        try:
            json_data = json.loads(conteudo)
            for escala in json_data.get("escalas", []):
                dados.append({"Arquivo": nome_arquivo, "Escala": escala.get("NOME", "")})
        except Exception as e:
            st.warning(f"Erro ao processar o arquivo {nome_arquivo}: {e}")
    
    with st.container(border=True):
        if dados:
            st.markdown("#### 📋 Tabela de Dados")
            df = pd.DataFrame(dados, columns=["Arquivo", "Escala"])
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name="lista_arquivos_escalas.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("❌ Nenhuma escala encontrada no banco de dados.")


if menu == "📄 Documentação Recursos":
    st.header("📄 Documentação Recursos (gestao de escalas.html)")
    st.write("Este é o relatório técnico gerado pelo PyInstaller, mostrando as dependências e módulos importados pela aplicação.")

    # Caminho para o seu arquivo HTML dentro do repositório
    html_file_path = 'gestao de escalas.html'

    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
            
        with st.container(border=True):
            # Renderiza o HTML na página
            components.html(source_code, height=600, scrolling=True)

    except FileNotFoundError:
        st.error(f"Erro: O arquivo {html_file_path} não foi encontrado no repositório.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar ler o arquivo HTML: {e}")