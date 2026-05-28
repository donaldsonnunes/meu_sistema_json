# processador.py (Versão Final com Lógica Unificada e Correta)

import pandas as pd
import json
import re
import uuid
from datetime import datetime, timedelta

# ==============================================================================
# SEÇÃO 1: TRADUTOR DE HORÁRIOS
# ==============================================================================

def get_day_indices(day_str):
    if not isinstance(day_str, str): return []
    day_map = {'SEG':0,'SEGUNDA':0,'2A':0,'2ª':0,'TER':1,'TERCA':1,'TERÇA':1,'3A':1,'3ª':1,'QUA':2,'QUARTA':2,'4A':2,'4ª':2,'QUI':3,'QUINTA':3,'5A':3,'5ª':3,'SEX':4,'SEXTA':4,'6A':4,'6ª':4,'SAB':5,'SABADO':5,'SÁBADO':5,'SÁB':5,'DOM':6,'DOMINGO':6}
    indices, day_str_upper = set(), day_str.upper().strip()
    range_match = re.search(r'([A-Z0-9ª]+)\s+(?:A|ATE|ATÉ)\s+([A-Z0-9ª]+)', day_str_upper)
    if range_match:
        start_day, end_day = day_map.get(range_match.group(1)), day_map.get(range_match.group(2))
        if start_day is not None and end_day is not None: return sorted(list(range(start_day, end_day + 1)))
    sanitized_str = re.sub(r'[/,]', ' ', day_str_upper)
    for part in filter(None, re.split(r'\s+', sanitized_str)):
        if (idx := day_map.get(part)) is not None: indices.add(idx)
    return sorted(list(indices))

def traduzir_horarios(df, coluna_origem, dicionario_regras):
    log_depuracao = []
    def _limpar_texto(texto):
        if not isinstance(texto, str): return ""
        texto_upper = texto.upper().strip()
        texto_limpo = re.sub(r'IRIS KRAUSE.*|DIARISTA|RECIFE|FEIRA|ÀS', '', texto_upper, flags=re.IGNORECASE)
        if not any(kw in texto_upper for kw in ['(IMPAR)', '(PAR)']):
            texto_limpo = texto_limpo.replace('(', ' ').replace(')', ' ')
        return re.sub(r'\s+', ' ', texto_limpo).strip()
    def _formatar_batidas(time_tokens, sep=" / "):
        batidas = []
        for t in time_tokens:
            n = re.sub(r'[^0-9]', '', str(t).replace('H',''))
            if not n: continue
            if len(n) <= 2: batidas.append(f"{int(n):02d}:00")
            elif len(n) == 3: batidas.append(f"0{n[0]}:{n[1:]}")
            elif len(n) >= 4: batidas.append(f"{n[:2]}:{n[2:4]}")
        return sep.join(batidas)
    def _formatar_dias(day_indices):
        if not day_indices: return ""
        day_map = {0:'SEG', 1:'TER', 2:'QUA', 3:'QUI', 4:'SEX', 5:'SAB', 6:'DOM'}
        dias_ordenados = sorted(list(set(day_indices)))
        grupos, grupo_atual = [], []
        for idx in dias_ordenados:
            if not grupo_atual or idx == grupo_atual[-1] + 1: grupo_atual.append(idx)
            else: grupos.append(grupo_atual); grupo_atual = [idx]
        if grupo_atual: grupos.append(grupo_atual)
        if not any(len(g) > 2 for g in grupos): return " ".join([day_map[idx] for idx in dias_ordenados])
        partes_dias = []
        for grupo in grupos:
            if len(grupo) > 2: partes_dias.append(f"{day_map[grupo[0]]} A {day_map[grupo[-1]]}")
            else: partes_dias.append(" ".join([day_map[idx] for idx in grupo]))
        return " E ".join(partes_dias)
    def _calcular_duracao(horarios_tokens):
        if len(horarios_tokens) < 2: return None
        try:
            t1_str = _formatar_batidas([horarios_tokens[0]], sep='').replace(':', ''); t2_str = _formatar_batidas([horarios_tokens[-1]], sep='').replace(':', '')
            h1, h2 = datetime.strptime(t1_str, "%H%M"), datetime.strptime(t2_str, "%H%M")
            if h2 < h1: h2 += timedelta(days=1)
            return h2 - h1
        except: return None
    def _parser_generico_fallback(texto):
        partes = re.split(r'(?=\b(?:SEG|TER|QUA|QUI|SEX|SAB|DOM|2ª|3ª|4ª|5ª|6ª)\b)', texto, flags=re.IGNORECASE)
        resultados_partes = []
        for parte in filter(None, partes):
            parte_strip = parte.strip()
            if not parte_strip: continue
            dias, horarios = get_day_indices(parte_strip), re.findall(r'(\d{1,2}:?\d{2})', parte_strip)
            if not dias and horarios: dias = list(range(5))
            if dias and horarios:
                dias_formatados = _formatar_dias(dias)
                separador_horario = ' AS ' if len(horarios) == 2 else ' / '
                horarios_formatados = _formatar_batidas(horarios, sep=separador_horario)
                resultados_partes.append(f"{dias_formatados} {horarios_formatados}")
        if resultados_partes: return " E ".join(resultados_partes)
        return None
    def _traduzir_linha(texto_original, index_linha):
        log_depuracao.append(f"\n--- [Linha {index_linha+2}] Analisando: '{texto_original}'")
        if not isinstance(texto_original, str) or not texto_original.strip(): log_depuracao.append("    --> FALHA: Descrição vazia."); return "SEM INTERPRETAÇÃO"
        texto_upper, texto_limpo = texto_original.upper().strip(), _limpar_texto(texto_original)
        log_depuracao.append(f"    Texto Limpo para Análise: '{texto_limpo}'")
        horarios_tokens = re.findall(r'(\d{1,2}H|\d{1,2}:\d{2})', texto_upper)
        for regra in dicionario_regras:
            log_depuracao.append(f"    - Testando Regra (Prioridade {regra['prioridade']}): '{regra['nome_regra']}'")
            if regra['tipo_regra'] == 'EXATA' and regra['condicao_texto'].upper() == texto_upper: log_depuracao.append(f"    --> SUCESSO: Regra 'EXATA'."); return regra['formato_saida']
            elif regra['tipo_regra'] == 'QUANTIDADE' and len(horarios_tokens) == regra['condicao_qtde_horarios']:
                cond_sem_dia_ok = not (regra['condicao_sem_dia'] and get_day_indices(texto_limpo))
                if cond_sem_dia_ok:
                    format_dict = {f"h{i+1}": _formatar_batidas([h], sep='') for i, h in enumerate(horarios_tokens)}; log_depuracao.append(f"    --> SUCESSO: Regra 'QUANTIDADE'."); return regra['formato_saida'].format(**format_dict)
            elif regra['tipo_regra'] == 'DURACAO':
                palavras_chave = [kw.strip().upper() for kw in (regra['condicao_texto'] or "").split(',') if kw.strip()]
                if palavras_chave and not all(kw in texto_upper for kw in palavras_chave): continue
                duracao_ok = False
                if not regra['condicao_duracao']: duracao_ok = True
                else:
                    duracao_total = _calcular_duracao(horarios_tokens)
                    if duracao_total:
                        try:
                            h, m = map(int, regra['condicao_duracao'].split(':'))
                            if duracao_total == timedelta(hours=h, minutes=m): duracao_ok = True
                        except: pass
                if duracao_ok:
                    format_dict = {f"h{i+1}": _formatar_batidas([h], sep='') for i, h in enumerate(horarios_tokens)}; log_depuracao.append(f"    --> SUCESSO: Regra 'DURACAO'."); return regra['formato_saida'].format(**format_dict)
        resultado_fallback = _parser_generico_fallback(texto_limpo)
        if resultado_fallback: return resultado_fallback
        log_depuracao.append("    --> FALHA: Nenhuma regra ou análise conseguiu interpretar o texto.")
        return "SEM INTERPRETAÇÃO"
    nome_coluna_destino = "DESCRICAO_TRADUZIDA"
    if nome_coluna_destino in df.columns: df = df.drop(columns=[nome_coluna_destino])
    resultados = [ _traduzir_linha(row[coluna_origem], i) for i, row in df.iterrows() ]
    df[nome_coluna_destino] = resultados
    return df, log_depuracao

# ==============================================================================
# SEÇÃO 2: PROCESSADOR DE ESCALAS
# ==============================================================================

def _criar_jornada_padrao(horarios):
    nome_jornada = " / ".join(horarios)
    batidas_formatadas = [h.replace(":", "") for h in horarios]
    periodos_expediente = []
    if len(batidas_formatadas) >= 2: periodos_expediente.append({"TM_HORA_INICIO": batidas_formatadas[0], "TM_HORA_FIM": batidas_formatadas[1], "DESC_TIPO_HORA": "Expediente"})
    if len(batidas_formatadas) == 4: periodos_expediente.append({"TM_HORA_INICIO": batidas_formatadas[2], "TM_HORA_FIM": batidas_formatadas[3], "DESC_TIPO_HORA": "Expediente"})
    return {"NOME_JORNADA": nome_jornada,"DESC_JORNADA": "","HORAS_CONTRATUAIS": horarios,"TRATAMENTO_EXPEDIENTE_EXTRA": "","TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "","FL_HORA_COMPENSAVEL": "1","FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "","FL_FATOR_POSTERIOR": "1","FL_TRATAMENTO_CARGA_INFERIOR": "FALTA","FL_TRATAMENTO_CARGA_SUPERIOR": "Hora Extra 50%","PREASSINALA_SOMENTE_BATIDAS_PARES": False,"batida_automatica": [],"PERIODOS": periodos_expediente, "key": uuid.uuid4().hex,"HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""]}

def process_file(df, output_path):
    log_unificacao = []
    data = {"escalas": [],"jornadas": {}, "horas_adicionais": {}}
    data["jornadas"]["ID_FOLGA"] = {"NOME_JORNADA": "FOLGA", "key": "ID_FOLGA", "sem_expediente": "1"}
    data["jornadas"]["ID_DSR"] = {"NOME_JORNADA": "DSR", "key": "ID_DSR", "FL_DSR": "1", "sem_expediente": "1"}
    data['horas_adicionais'] = {"Hora Extra 50%": {"TIPO": "HE", "VALOR": "50"},"Hora Extra 100%": {"TIPO": "HE", "VALOR": "100"}, "Banco de Horas 50%": {"TIPO": "BH", "VALOR": "1"},"Banco de Horas 100%": {"TIPO": "BH", "VALOR": "1"}}
    mapa_escalas_existentes = {}

    col_descricao_traduzida = "DESCRICAO_TRADUZIDA"
    col_nome = "NOME" if "NOME" in df.columns else col_descricao_traduzida
    col_codigo = "COD" if "COD" in df.columns else "CODIGO"
    col_carga_horaria = "CARGA_HORARIA" if "CARGA_HORARIA" in df.columns else "carga_horaria"
    
    for index, row in df.iterrows():
        descricao_escala = str(row.get(col_descricao_traduzida, "")).upper()
        if not descricao_escala or "SEM INTERPRETAÇÃO" in descricao_escala: continue
        if descricao_escala in mapa_escalas_existentes: log_unificacao.append(f"Escala '{row[col_nome]}' (Linha {index + 2}) unificada com '{mapa_escalas_existentes[descricao_escala]}'."); continue

        escala = {"NOME": str(row.get(col_nome, descricao_escala)),"DESC_ESCALA": row.get(col_descricao_traduzida, ""),"COD": str(row.get(col_codigo, index + 1)),"carga_horaria": str(row.get(col_carga_horaria, "0")),"tipo_escala": "","dsr": { "ativo": "1", "dia_completo": "1", "desconto_valor_falta": "1", "apuracao": { "semanal": "1" } },"TIPO_HORA_ADICIONAL": "", "TIPO_HORA_ADICIONAL_NOTURNO": "", "COD_ADICIONAL_NOTURNO": "","excedente_apuracao_semanal": "", "deficit_apuracao_semanal": "", "excedente_apuracao_mensal": "","deficit_apuracao_mensal": "", "key": uuid.uuid4().hex}
        
        is_12x36 = '12X36' in descricao_escala or '12X35' in descricao_escala
        is_24h = '24:00' in descricao_escala or '23:59' in descricao_escala
        
        if is_12x36:
            escala["TIPO"] = "12X36"
            horarios = re.findall(r'(\d{2}:\d{2})', descricao_escala)
            if horarios:
                chave_jornada = " / ".join(horarios)
                jornada_existente = next((j for j in data["jornadas"].values() if j.get("NOME_JORNADA") == chave_jornada), None)
                if not jornada_existente:
                    nova_jornada = _criar_jornada_padrao(horarios); data["jornadas"][nova_jornada['key']] = nova_jornada
                    id_jornada_trabalho = nova_jornada['key']
                else: id_jornada_trabalho = jornada_existente['key']
                escala["JORNADAS"] = [id_jornada_trabalho, "ID_FOLGA"]
            else: escala["JORNADAS"] = ["ID_FOLGA", "ID_FOLGA"]
        elif is_24h:
            escala["TIPO"] = "DIARIA"
            horarios = re.findall(r'(\d{2}:\d{2})', descricao_escala)
            if horarios:
                chave_jornada = " / ".join(horarios)
                jornada_existente = next((j for j in data["jornadas"].values() if j.get("NOME_JORNADA") == chave_jornada), None)
                if not jornada_existente:
                    nova_jornada = _criar_jornada_padrao(horarios); data["jornadas"][nova_jornada['key']] = nova_jornada
                    id_jornada_trabalho = nova_jornada['key']
                else: id_jornada_trabalho = jornada_existente['key']
                escala["JORNADAS"] = [id_jornada_trabalho]
            else: escala["JORNADAS"] = ["ID_FOLGA"]
        else:
            escala["TIPO"] = "SEMANAL"
            jornadas_semana = ["ID_FOLGA"] * 7
            partes_escala = descricao_escala.split(' E ')
            for parte in partes_escala:
                horarios = re.findall(r'(\d{2}:\d{2})', parte)
                if not horarios: continue
                dias_str = re.sub(r'\d{2}:\d{2}', '', parte).replace('AS', '').strip()
                indices_dias = get_day_indices(dias_str)
                if not indices_dias: continue
                chave_jornada = " / ".join(horarios)
                jornada_existente = next((j for j in data["jornadas"].values() if j.get("NOME_JORNADA") == chave_jornada), None)
                if not jornada_existente:
                    nova_jornada = _criar_jornada_padrao(horarios); data["jornadas"][nova_jornada['key']] = nova_jornada
                    id_jornada = nova_jornada['key']
                else: id_jornada = jornada_existente['key']
                for idx in indices_dias:
                    if 0 <= idx < 7: jornadas_semana[idx] = id_jornada
            if jornadas_semana[6] == "ID_FOLGA": jornadas_semana[6] = "ID_DSR"
            else:
                try: primeira_folga_idx = jornadas_semana.index("ID_FOLGA"); jornadas_semana[primeira_folga_idx] = "ID_DSR"
                except ValueError: pass
            escala["JORNADAS"] = jornadas_semana

        data["escalas"].append(escala)
        mapa_escalas_existentes[descricao_escala] = row[col_nome]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    return data, log_unificacao
