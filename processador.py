# processador.py (Versão Final, Completa e Funcional)

import pandas as pd
import json
import re
import uuid
from datetime import datetime, timedelta

# =====================================================================================
# FUNÇÕES AUXILIARES (Com a correção final)
# =====================================================================================

def generate_key(): return uuid.uuid4().hex
def format_time_to_hhmm(t): return re.sub(r'[^0-9]', '', str(t))[:4] if t else ""
def format_time_to_hh_mm(t):
    if not t: return ""
    c = re.sub(r'[^0-9]', '', str(t))
    return f"{c[:2]}:{c[2:4]}" if len(c) >= 4 else str(t)

def standardize_time_range(t):
    """Padroniza uma string de tempo para o formato universal (ex: 0700AS1700)."""
    if not t: return ""
    # CORREÇÃO FINAL: Garante que os dois-pontos (:) sejam removidos
    temp_str = str(t).upper().replace('-', 'AS').replace('ÀS', 'AS')
    return re.sub(r'[^0-9AS]', '', temp_str)

def get_day_indices(day_str):
    day_map = {'SEG':0,'SEGUNDA':0,'2A':0,'2ª':0,'TER':1,'TERCA':1,'TERÇA':1,'3A':1,'3ª':1,'QUA':2,'QUARTA':2,'4A':2,'4ª':2,'QUI':3,'QUINTA':3,'5A':3,'5ª':3,'SEX':4,'SEXTA':4,'6A':4,'6ª':4,'SAB':5,'SABADO':5,'SÁBADO':5,'SÁB':5,'DOM':6,'DOMINGO':6}
    indices, day_str_upper = set(), day_str.upper().strip()
    range_match = re.search(r'([A-Z0-9ª]+)\s+(?:A|ATE|ATÉ)\s+([A-Z0-9ª]+)', day_str_upper)
    if range_match:
        start_day, end_day = day_map.get(range_match.group(1)), day_map.get(range_match.group(2))
        if start_day is not None and end_day is not None: return sorted(list(range(start_day, end_day + 1)))
    sanitized_str = re.sub(r'[/,]', ' ', day_str_upper)
    sanitized_str = re.sub(r'\b(A|E|DAS)\b', ' ', sanitized_str)
    for part in filter(None, re.split(r'\s+', sanitized_str)):
        if (idx := day_map.get(part)) is not None: indices.add(idx)
    return sorted(list(indices))

def generate_periods_from_punches(punches: list):
    if not punches or len(punches) % 2 != 0: return []
    periods = [{"TM_HORA_INICIO": "0000", "TM_HORA_FIM": format_time_to_hhmm(punches[0]), "DESC_TIPO_HORA": "Hora Extra 50%"}]
    for i in range(0, len(punches), 2):
        start_hhmm, end_hhmm = format_time_to_hhmm(punches[i]), format_time_to_hhmm(punches[i+1])
        periods.append({"TM_HORA_INICIO": start_hhmm, "TM_HORA_FIM": end_hhmm, "DESC_TIPO_HORA": "Expediente"})
        if i + 2 < len(punches): periods.append({"TM_HORA_INICIO": end_hhmm, "TM_HORA_FIM": format_time_to_hhmm(punches[i+2]), "DESC_TIPO_HORA": "Hora Extra 50%"})
    periods.append({"TM_HORA_INICIO": format_time_to_hhmm(punches[-1]), "TM_HORA_FIM": "2400", "DESC_TIPO_HORA": "Hora Extra 50%"})
    return periods

def create_jornada_object(nome_jornada_raw):
    contractual_hours, batida_automatica, nome_jornada_display = [], [], nome_jornada_raw
    if "_E_" in nome_jornada_raw:
        main_part, interval_part = nome_jornada_raw.split("_E_", 1)
        main_match, interval_match = re.match(r'(\d{4})AS(\d{4})', main_part), re.match(r'(\d{4})AS(\d{4})', interval_part)
        if main_match and interval_match:
            start_fmt, end_fmt = format_time_to_hh_mm(main_match.group(1)), format_time_to_hh_mm(main_match.group(2))
            break_start_fmt, break_end_fmt = format_time_to_hh_mm(interval_match.group(1)), format_time_to_hh_mm(interval_match.group(2))
            contractual_hours = [start_fmt, break_start_fmt, break_end_fmt, end_fmt]
            batida_automatica = [format_time_to_hhmm(break_start_fmt), format_time_to_hhmm(break_end_fmt)]
            nome_jornada_display = f"{start_fmt} AS {end_fmt}"
    else:
        main_match = re.match(r'(\d{4})AS(\d{4})', nome_jornada_raw)
        if main_match:
            start_fmt, end_fmt = format_time_to_hh_mm(main_match.group(1)), format_time_to_hh_mm(main_match.group(2))
            nome_jornada_display = f"{start_fmt} AS {end_fmt}"
            start_dt, end_dt = datetime.strptime(start_fmt, "%H:%M"), datetime.strptime(end_fmt, "%H:%M")
            if end_dt <= start_dt: end_dt += timedelta(days=1)
            if (end_dt - start_dt).total_seconds() / 3600 > 6:
                mid_dt = start_dt + timedelta(seconds=(end_dt - start_dt).total_seconds() / 2)
                break_start, break_end = mid_dt - timedelta(minutes=30), mid_dt + timedelta(minutes=30)
                contractual_hours = [start_dt.strftime("%H:%M"), break_start.strftime("%H:%M"), break_end.strftime("%H:%M"), end_dt.strftime("%H:%M")]
                batida_automatica = [format_time_to_hhmm(break_start.strftime("%H:%M")), format_time_to_hhmm(break_end.strftime("%H:%M"))]
            else:
                contractual_hours = [start_fmt, end_fmt]
    return {"NOME_JORNADA": nome_jornada_display, "HORAS_CONTRATUAIS": contractual_hours, "PREASSINALA_SOMENTE_BATIDAS_PARES": bool(batida_automatica), "batida_automatica": batida_automatica, "PERIODOS": generate_periods_from_punches(contractual_hours), "key": generate_key()}

def _ensure_special_jornadas_exist(jornadas_dict):
    if "ID_DSR" not in jornadas_dict: jornadas_dict["ID_DSR"] = {"NOME_JORNADA": "DSR", "key": "ID_DSR", "HORAS_CONTRATUAIS": [],"PERIODOS":[]}
    if "ID_FOLGA" not in jornadas_dict: jornadas_dict["ID_FOLGA"] = {"NOME_JORNADA": "FOLGA", "key": "ID_FOLGA", "HORAS_CONTRATUAIS": [], "PERIODOS":[]}

def process_schedule_description(desc, jornada_map, all_jornadas):
    desc_upper = desc.upper().strip()
    _ensure_special_jornadas_exist(all_jornadas)
    time_regex = r'(\d{2}:?\d{2}\s*AS\s*\d{2}:?\d{2}(?:\s*E\s*\d{2}:?\d{2}\s*-\s*\d{2}:?\d{2})?)'
    if re.search(r'\b12X36\b', desc_upper):
        tipo_escala, time_match = "12X36", re.search(r'\d{2}:?\d{2}\s*AS\s*\d{2}:?\d{2}', desc_upper)
        time_range = time_match.group(0) if time_match else ("19:00 AS 07:00" if "NOTURNO" in desc_upper else "07:00 AS 19:00")
        std_time = standardize_time_range(time_range)
        if std_time not in jornada_map: jornada_map[std_time] = create_jornada_object(std_time)
        jornada_key = jornada_map[std_time]['key']
        all_jornadas[jornada_key] = jornada_map[std_time]
        return [jornada_key, "ID_FOLGA"], tipo_escala
    else:
        tipo_escala, jornadas_semanais = "SEMANAL", ["ID_FOLGA"] * 7
        times_found, days_found = re.findall(time_regex, desc_upper), re.split(time_regex, desc_upper)
        days_found = [d.strip() for d in days_found if d and d.strip() and d not in times_found]
        for i in range(len(times_found)):
            days_part, times_part = (days_found[i] if i < len(days_found) else ""), times_found[i]
            day_indices = get_day_indices(days_part)
            horario_str = f"{standardize_time_range(times_part.split(' E ', 1)[0])}_E_{standardize_time_range(times_part.split(' E ', 1)[1])}" if " E " in times_part else standardize_time_range(times_part)
            if horario_str not in jornada_map: jornada_map[horario_str] = create_jornada_object(horario_str)
            jornada_key = jornada_map[horario_str]['key']
            all_jornadas[jornada_key] = jornada_map[horario_str]
            for idx in day_indices:
                if 0 <= idx < 7: jornadas_semanais[idx] = jornada_key
        if jornadas_semanais[6] == "ID_FOLGA": jornadas_semanais[6] = "ID_DSR"
        return jornadas_semanais, tipo_escala

def calculate_carga_horaria(jornadas_list, all_jornadas_defs):
    total_seconds = 0
    for key in jornadas_list:
        if key in all_jornadas_defs and key not in ["ID_DSR", "ID_FOLGA"]:
            jornada = all_jornadas_defs[key]
            horas = jornada.get("HORAS_CONTRATUAIS", [])
            for i in range(0, len(horas), 2):
                if i + 1 < len(horas):
                    try:
                        start_dt, end_dt = datetime.strptime(horas[i], "%H:%M"), datetime.strptime(horas[i+1], "%H:%M")
                        if end_dt <= start_dt: end_dt += timedelta(days=1)
                        total_seconds += (end_dt - start_dt).total_seconds()
                    except (ValueError, TypeError): continue
    return str(int(total_seconds / 3600))

def process_file(df, output_json_path):
    all_jornadas_defs, jornada_map, escalas_unicas = {}, {}, {}
    # Lista para o novo log de unificação
    log_unificacao = []
    
    for _, row in df.iterrows():
        cod, nome, desc = str(row.get('CODIGO', '')), str(row.get('NOME_DA_ESCALA', '')), str(row.get('DESCRICAO_DA_ESTRUTURA', ''))
        
        if not desc or pd.isna(desc):
            # Escalas com descrição vazia ainda podem ser consideradas "desprezadas"
            # mas o foco agora é na unificação. Vamos ignorá-las por enquanto.
            continue
        
        try:
            # Etapa 1: Processa a escala individualmente para obter sua estrutura
            jornadas, tipo = process_schedule_description(desc, jornada_map, all_jornadas_defs)
            
            # Etapa 2: Cria uma assinatura baseada no RESULTADO
            assinatura_resultado = (tuple(jornadas), tipo)
            
            # Etapa 3: Verifica se uma escala com este resultado já existe
            if assinatura_resultado in escalas_unicas:
                escala_existente = escalas_unicas[assinatura_resultado]
                
                # NOVO: Em vez de adicionar "ORIGENS", cria uma entrada de log
                log_entry = (
                    f"A escala Cód: {cod} (Nome: {nome}) foi unificada na escala "
                    f"Cód: {escala_existente['COD']} (Nome: {escala_existente['NOME']}) "
                    f"por ter estrutura idêntica."
                )
                log_unificacao.append(log_entry)
                
                continue # Pula para a próxima linha, unificando a escala atual
            
            # Se for uma escala nova, calcula a carga e a armazena
            carga = calculate_carga_horaria(jornadas, all_jornadas_defs)
            scale_obj = {
                "NOME": nome, "DESC_ESCALA": desc, "COD": cod,
                "carga_horaria": carga, "TIPO": tipo, "JORNADAS": jornadas,
                "key": generate_key()
            }
            escalas_unicas[assinatura_resultado] = scale_obj
        except Exception as e:
            # Mantemos um log de erros graves caso ocorram
            log_unificacao.append(f"ERRO GRAVE ao processar Cód: {cod} | Motivo: {e}")

    output_data = {"escalas": list(escalas_unicas.values()), "jornadas": all_jornadas_defs, "horas_adicionais": []}
    with open(output_json_path, 'w', encoding='utf-8') as f: json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    # Retorna o log de unificação em vez do log de desprezadas
    return output_data, log_unificacao