# processador.py
import pandas as pd
import json
import re
import uuid
from datetime import datetime, timedelta

# --- Funções auxiliares ---

def generate_key():
    return uuid.uuid4().hex[:24]

def format_time_to_hhmm(time_str):
    if time_str is None: return ""
    return re.sub(r'[^0-9]', '', str(time_str))[:4]

def format_time_to_hh_mm(time_str):
    if time_str is None: return ""
    cleaned = re.sub(r'[^0-9]', '', str(time_str))
    if len(cleaned) >= 4:
        return f"{cleaned[:2]}:{cleaned[2:4]}"
    return time_str

def standardize_time_range(time_range_str):
    if time_range_str is None: return ""
    return re.sub(r'\s+', '', time_range_str).replace('-', 'AS').replace('ÀS', 'AS').upper()

# --- Lógica de Geração de Jornada ---

def generate_periods_from_punches(punches: list):
    """Gera a lista de 'PERIODOS' a partir de uma lista de batidas HH:MM."""
    if not punches or len(punches) < 2 or len(punches) % 2 != 0:
        return []

    periods = []
    periods.append({
        "TM_HORA_INICIO": "0000",
        "TM_HORA_FIM": format_time_to_hhmm(punches[0]),
        "DESC_TIPO_HORA": "Hora Extra 50%"
    })

    for i in range(0, len(punches), 2):
        start_exp_hhmm = format_time_to_hhmm(punches[i])
        end_exp_hhmm = format_time_to_hhmm(punches[i+1])
        periods.append({"TM_HORA_INICIO": start_exp_hhmm, "TM_HORA_FIM": end_exp_hhmm, "DESC_TIPO_HORA": "Expediente"})
        
        if i + 2 < len(punches):
            interval_end_hhmm = format_time_to_hhmm(punches[i+2])
            periods.append({
                "TM_HORA_INICIO": end_exp_hhmm,
                "TM_HORA_FIM": interval_end_hhmm,
                "DESC_TIPO_HORA": "Hora Extra 50%"
            })

    last_punch_hhmm = format_time_to_hhmm(punches[-1])
    periods.append({
        "TM_HORA_INICIO": last_punch_hhmm,
        "TM_HORA_FIM": "2400",
        "DESC_TIPO_HORA": "Hora Extra 50%"
    })
    return periods

def create_jornada_object(nome_jornada_raw):
    """
    Cria um objeto de jornada com a lógica híbrida:
    1. Usa o intervalo explícito, se fornecido.
    2. Se não, calcula um intervalo automático para jornadas > 6h.
    """
    contractual_hours = []
    batida_automatica = []
    nome_jornada_display = nome_jornada_raw

    explicit_interval_match = re.search(r'E\s*(\d{2}:?\d{2})\s*(?:-|AS)\s*(\d{2}:?\d{2})', nome_jornada_raw, re.IGNORECASE)
    
    if explicit_interval_match:
        main_range_str = nome_jornada_raw[:explicit_interval_match.start()].strip()
        main_match = re.match(r'(\d{2}:?\d{2}).*?AS.*?(\d{2}:?\d{2})', main_range_str.replace(" ", ""))
        if main_match:
            main_start_fmt = format_time_to_hh_mm(main_match.group(1))
            main_end_fmt = format_time_to_hh_mm(main_match.group(2))
            break_start_fmt = format_time_to_hh_mm(explicit_interval_match.group(1))
            break_end_fmt = format_time_to_hh_mm(explicit_interval_match.group(2))
            contractual_hours = [main_start_fmt, break_start_fmt, break_end_fmt, main_end_fmt]
            batida_automatica = [format_time_to_hhmm(break_start_fmt), format_time_to_hhmm(break_end_fmt)]
            nome_jornada_display = f"{main_start_fmt} AS {main_end_fmt}"
    else:
        main_match = re.match(r'(\d{2}:?\d{2}).*?AS.*?(\d{2}:?\d{2})', nome_jornada_raw.replace(" ", ""))
        if main_match:
            start_time_fmt = format_time_to_hh_mm(main_match.group(1))
            end_time_fmt = format_time_to_hh_mm(main_match.group(2))
            nome_jornada_display = f"{start_time_fmt} AS {end_time_fmt}"
            start_dt = datetime.strptime(start_time_fmt, "%H:%M")
            end_dt = datetime.strptime(end_time_fmt, "%H:%M")
            if end_dt <= start_dt: end_dt += timedelta(days=1)
            duration_hours = (end_dt - start_dt).total_seconds() / 3600
            if duration_hours > 6:
                duration_seconds = (end_dt - start_dt).total_seconds()
                midpoint_dt = start_dt + timedelta(seconds=duration_seconds / 2)
                interval_start_dt = midpoint_dt - timedelta(minutes=30)
                interval_end_dt = midpoint_dt + timedelta(minutes=30)
                final_end_time = end_dt.strftime("%H:%M")
                if final_end_time == "00:00": final_end_time = "23:59"
                contractual_hours = [
                    start_dt.strftime("%H:%M"),
                    interval_start_dt.strftime("%H:%M"),
                    interval_end_dt.strftime("%H:%M"),
                    final_end_time
                ]
                batida_automatica = [
                    format_time_to_hhmm(contractual_hours[1]),
                    format_time_to_hhmm(contractual_hours[2])
                ]
            else:
                contractual_hours = [start_time_fmt, end_time_fmt]
    
    periods = generate_periods_from_punches(contractual_hours)
    jornada = {
        "NOME_JORNADA": nome_jornada_display, "DESC_JORNADA": "", "HORAS_CONTRATUAIS": contractual_hours,
        "TRATAMENTO_EXPEDIENTE_EXTRA": "", "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "",
        "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""], "FL_HORA_COMPENSAVEL": "1",
        "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "", "FL_FATOR_POSTERIOR": "1",
        "FL_TRATAMENTO_CARGA_INFERIOR": "FALTA", "FL_TRATAMENTO_CARGA_SUPERIOR": "Hora Extra 50%",
        "PREASSINALA_SOMENTE_BATIDAS_PARES": bool(batida_automatica),
        "batida_automatica": batida_automatica, "PERIODOS": periods,
        "TM_TOLERANCIA_CARGA_NEGATIVA": "0010", "TM_TOLERANCIA_CARGA_POSITIVA": "0010",
        "TM_INTINERE_ENTRADA": "", "TM_INTINERE_SAIDA": "", "TIPO_HORA_ADICIONAL": "Hora Extra 100%",
        "TIPO_HORA_ADICIONAL_NOTURNO": "Hora Extra 100%", "sem_expediente": None, "TM_HORA_INICIO": "0000",
        "TM_TOLERANCIA_ENTRADA_ANTECIPADA": None, "TM_TOLERANCIA_ENTRADA_TARDIA": None,
        "TM_TOLERANCIA_SAIDA_ANTECIPADA": None, "TM_TOLERANCIA_SAIDA_TARDIA": None,
        "key": generate_key()
    }
    return jornada

# --- Demais funções (sem alterações) ---

def get_day_indices(day_str):
    day_map = {
        'SEG': 0, '2ª': 0, '2A': 0, 'SEGUNDA': 0, 'TER': 1, '3ª': 1, '3A': 1, 'TERÇA': 1, 'TERCA': 1,
        'QUA': 2, '4ª': 2, '4A': 2, 'QUARTA': 2, 'QUI': 3, '5ª': 3, '5A': 3, 'QUINTA': 3,
        'SEX': 4, '6ª': 4, '6A': 4, 'SEXTA': 4, 'SAB': 5, 'SÁB': 5, 'SABADO': 5, 'SÁBADO': 5,
        'DOM': 6, 'DOMINGO': 6
    }
    indices = set()
    day_str = day_str.upper().strip().replace('DAS', '').strip()
    range_match = re.search(r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]+)\s*A\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]+)', day_str)
    if range_match:
        start_day, end_day = range_match.groups()
        start_index, end_index = day_map.get(start_day), day_map.get(end_day)
        if start_index is not None and end_index is not None:
            indices.update(range(start_index, end_index + 1))
            return sorted(list(indices))
    day_parts = re.split(r'[,\s]+', day_str)
    for part in filter(None, day_parts):
        idx = day_map.get(part)
        if idx is not None: indices.add(idx)
    return sorted(list(indices))

def _ensure_special_jornadas_exist(all_jornadas_definitions):
    """
    Garante que as jornadas especiais DSR e FOLGA são definidas com
    a estrutura e os valores padrão corretos.
    """
    # Define a estrutura padrão para DSR conforme o exemplo fornecido.
    if "ID_DSR" not in all_jornadas_definitions:
        all_jornadas_definitions["ID_DSR"] = {
            "NOME_JORNADA": "DSR",
            "DESC_JORNADA": "",
            "virada_dia_anterior": "1",
            "FL_DSR": "1",
            "TRATAMENTO_EXPEDIENTE_EXTRA": "",
            "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "",
            "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""],
            "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "",
            "FL_TRATAMENTO_CARGA_INFERIOR": "",
            "FL_TRATAMENTO_CARGA_SUPERIOR": "",
            "TM_TOLERANCIA_ENTRADA_ANTECIPADA": "0000",
            "TM_TOLERANCIA_ENTRADA_TARDIA": "0000",
            "TM_TOLERANCIA_MAXIMA": "",
            "TM_TOLERANCIA_SAIDA_ANTECIPADA": "0000",
            "TM_TOLERANCIA_SAIDA_TARDIA": "0000",
            "TM_TOLERANCIA_CARGA_NEGATIVA": "",
            "TM_TOLERANCIA_CARGA_POSITIVA": "",
            "TM_INTINERE_ENTRADA": "",
            "TM_INTINERE_SAIDA": "",
            "TIPO_HORA_ADICIONAL": "",
            "TIPO_HORA_ADICIONAL_NOTURNO": "",
            "PERIODOS": [{
                "TM_HORA_INICIO": "0000",
                "TM_HORA_FIM": "2400",
                "DESC_TIPO_HORA": "Hora extra 100%"
            }],
            "sem_expediente": "1",
            "TM_HORA_INICIO": "0000",
            "key": "ID_DSR"  # Chave fixa para o DSR
        }
        
    # Define uma estrutura padrão e vazia para FOLGA.
    if "ID_FOLGA" not in all_jornadas_definitions:
        all_jornadas_definitions["ID_FOLGA"] = {
            "NOME_JORNADA": "FOLGA",
            "DESC_JORNADA": "Dia de Folga",
            "HORAS_CONTRATUAIS": [],
            "PERIODOS": [],
            "key": "ID_FOLGA" # Chave fixa para FOLGA
        }
def process_schedule_description(description, jornada_mapping, all_jornadas):
    """
    Processa a descrição da escala, tratando 12x36 como um ciclo de 2 dias.
    """
    desc_upper = re.sub(r'\s+', ' ', description.upper().replace('\n', ' ')).strip()
    jornadas_semanais = ["ID_FOLGA"] * 7
    scale_type = "SEMANAL"

    if "12X36" in desc_upper:
        scale_type = "12X36"
        time_match = re.search(r'(\d{2}:?\d{2}.*?AS.*?\d{2}:?\d{2})', desc_upper)
        time_range = time_match.group(1) if time_match else "07:00 AS 19:00" # Horário padrão para 12h
        
        standardized_time = standardize_time_range(time_range)
        if standardized_time not in jornada_mapping:
            # Para 12x36, a jornada de trabalho tem 12h, então não deve ter intervalo automático
            # Criamos um objeto de jornada especial para 12h diretas.
            jornada_12h = {
                "NOME_JORNADA": f"{format_time_to_hh_mm(time_range.split('AS')[0])} AS {format_time_to_hh_mm(time_range.split('AS')[1])}",
                "DESC_JORNADA": "",
                "HORAS_CONTRATUAIS": [format_time_to_hh_mm(t) for t in time_range.split('AS')],
                "TRATAMENTO_EXPEDIENTE_EXTRA": "", "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "","HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""],"FL_HORA_COMPENSAVEL": "1","FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "","FL_FATOR_POSTERIOR": "1","FL_TRATAMENTO_CARGA_INFERIOR": "FALTA","FL_TRATAMENTO_CARGA_SUPERIOR": "Hora Extra 50%","PREASSINALA_SOMENTE_BATIDAS_PARES": False,"batida_automatica": [],"PERIODOS": generate_periods_from_punches([format_time_to_hh_mm(t) for t in time_range.split('AS')]),
                "TM_TOLERANCIA_CARGA_NEGATIVA": "0010","TM_TOLERANCIA_CARGA_POSITIVA": "0010","TM_INTINERE_ENTRADA": "","TM_INTINERE_SAIDA": "","TIPO_HORA_ADICIONAL": "Hora Extra 100%","TIPO_HORA_ADICIONAL_NOTURNO": "Hora Extra 100%","sem_expediente": None,"TM_HORA_INICIO": "0000",
                "TM_TOLERANCIA_ENTRADA_ANTECIPADA": None,"TM_TOLERANCIA_ENTRADA_TARDIA": None,"TM_TOLERANCIA_SAIDA_ANTECIPADA": None,"TM_TOLERANCIA_SAIDA_TARDIA": None,"key": generate_key()
            }
            jornada_mapping[standardized_time] = jornada_12h
        
        jornada_key = jornada_mapping[standardized_time]['key']
        all_jornadas[jornada_key] = jornada_mapping[standardized_time]

        # --- PONTO DA ALTERAÇÃO ---
        # A lista de jornadas agora contém apenas 2 elementos para o ciclo 12x36
        jornadas_semanais = [jornada_key, "ID_FOLGA"]
        
        _ensure_special_jornadas_exist(all_jornadas)
        return jornadas_semanais, scale_type

    time_regex = r'(\d{2}:\d{2}(?::\d{2})?\s*AS\s*\d{2}:\d{2}(?::\d{2})?\s*(?:E\s*\d{2}:?\d{2}\s*(?:-|AS)\s*\d{2}:?\d{2})?)'
    chunks = re.split(time_regex, desc_upper, flags=re.IGNORECASE)
    chunks = [chunk for chunk in chunks if chunk and chunk.strip()]
    for i in range(0, len(chunks) // 2 * 2, 2):
        days_part = chunks[i].strip()
        times_part = chunks[i+1].strip()
        day_indices = get_day_indices(days_part)
        if not day_indices: continue
        standardized_time = standardize_time_range(times_part)
        if standardized_time not in jornada_mapping:
            jornada_mapping[standardized_time] = create_jornada_object(times_part)
        current_jornada_key = jornada_mapping[standardized_time]['key']
        all_jornadas[current_jornada_key] = jornada_mapping[standardized_time]
        for idx in day_indices:
            if 0 <= idx < 7: jornadas_semanais[idx] = current_jornada_key

    if jornadas_semanais[6] == "ID_FOLGA":
        jornadas_semanais[6] = "ID_DSR"
    _ensure_special_jornadas_exist(all_jornadas)
    return jornadas_semanais, scale_type

def calculate_carga_horaria(jornadas_list, all_jornadas_definitions):
    total_minutes = 0
    for jornada_key in jornadas_list:
        if jornada_key in all_jornadas_definitions and jornada_key not in ["ID_DSR", "ID_FOLGA"]:
            jornada_obj = all_jornadas_definitions[jornada_key]
            horas_contratuais = jornada_obj.get("HORAS_CONTRATUAIS", [])
            if len(horas_contratuais) >= 2:
                 start_dt = datetime.strptime(horas_contratuais[0], "%H:%M")
                 end_dt = datetime.strptime(horas_contratuais[1], "%H:%M")
                 if end_dt <= start_dt: end_dt += timedelta(days=1)
                 total_minutes += (end_dt - start_dt).total_seconds() / 60
            if len(horas_contratuais) == 4:
                 start2_dt = datetime.strptime(horas_contratuais[2], "%H:%M")
                 end2_dt = datetime.strptime(horas_contratuais[3], "%H:%M")
                 if end2_dt <= start2_dt: end2_dt += timedelta(days=1)
                 total_minutes += (end2_dt - start2_dt).total_seconds() / 60
    return str(round(total_minutes / 60))


def process_file(df, output_json_path):
    df.columns = [str(col).upper().replace(' ', '_') for col in df.columns]
    required_cols = ['CODIGO', 'NOME_DA_ESCALA', 'DESCRICAO_DA_ESTRUTURA']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Cabeçalhos do arquivo ausentes. Esperado: {', '.join(required_cols)}")

    all_scales = []
    all_jornadas_definitions = {}
    jornada_mapping = {}

    for _, row in df.iterrows():
        cod = str(row.get('CODIGO', ''))
        nome_escala = str(row.get('NOME_DA_ESCALA', ''))
        descricao_estrutura = str(row.get('DESCRICAO_DA_ESTRUTURA', ''))

        jornadas_for_scale, tipo_escala = process_schedule_description(
            descricao_estrutura, jornada_mapping, all_jornadas_definitions
        )
        carga_horaria = calculate_carga_horaria(jornadas_for_scale, all_jornadas_definitions)
        
        scale_obj = {
            "NOME": nome_escala, "DESC_ESCALA": descricao_estrutura, "COD": cod,
            "carga_horaria": carga_horaria, "tipo_escala": "", "TIPO": tipo_escala,
            "JORNADAS": jornadas_for_scale,
            "dsr": {"ativo": "1", "dia_completo": "1", "desconto_valor_falta": "1", "apuracao": {"semanal": "1"}},
            "TIPO_HORA_ADICIONAL": "", "TIPO_HORA_ADICIONAL_NOTURNO": "", "COD_ADICIONAL_NOTURNO": "",
            "excedente_apuracao_semanal": "", "deficit_apuracao_semanal": "",
            "excedente_apuracao_mensal": "", "deficit_apuracao_mensal": "",
            "key": generate_key()
        }
        all_scales.append(scale_obj)
    
    output_data = {
        "escalas": all_scales,
        "jornadas": all_jornadas_definitions,
        "horas_adicionais": []
    }

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    return output_data