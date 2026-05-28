# gerenciador_escalas_final.py
# Leitura de CSV com cabeçalhos variados e parser robusto para DESC_ESCALA
# Garante tratamento de "E SAB", ranges "SEG A SEX" e reaproveitamento de jornada para mesmos horários.

import csv
import json
import re
import uuid

def gerar_id():
    return uuid.uuid4().hex

# mapa de dias para índices (SEG=0 .. DOM=6)
DAY_MAP = {'SEG':0,'TER':1,'QUA':2,'QUI':3,'SEX':4,'SAB':5,'DOM':6}

# regex para tokens de dia (ex: SEG, SEG-SEX)
DAY_TOKEN_RE = re.compile(r'\b(?:SEG|TER|QUA|QUI|SEX|SAB|DOM)(?:-(?:SEG|TER|QUA|QUI|SEX|SAB|DOM))?\b', flags=re.IGNORECASE)

def expand_day_token(tok):
    """Expande token de dia (ex: 'SEG' -> [0], 'SEG-SEX' -> [0,1,2,3,4])"""
    tok = tok.upper()
    if '-' in tok:
        a,b = tok.split('-',1)
        return list(range(DAY_MAP[a], DAY_MAP[b]+1))
    return [DAY_MAP[tok]]

def format_time_hhmm_to_hh_mm(time_hhmm_str):
    """Converte 'HHMM' para 'HH:MM'."""
    if time_hhmm_str is None:
        return ""
    time_hhmm_str = str(time_hhmm_str)
    if len(time_hhmm_str) == 4 and time_hhmm_str.isdigit():
        return f"{time_hhmm_str[:2]}:{time_hhmm_str[2:]}"
    return time_hhmm_str

def format_time_hh_mm_to_hhmm(time_hh_mm_str):
    """Converte 'HH:MM' para 'HHMM'."""
    if time_hh_mm_str is None:
        return ""
    return re.sub(r'[^0-9]', '', str(time_hh_mm_str))

def parse_desc_escala(desc, all_jornadas):
    """
    Converte a descrição da escala em lista de 7 jornadas (SEG..DOM).
    - Trata 'E SAB' / ' E ' variants
    - Converte 'SEG A SEX' -> 'SEG-SEX' e expande o intervalo
    - Reaproveita o mesmo id de jornada quando o conjunto de horários é idêntico
    """
    if not desc:
        return ["ID_FOLGA"] * 6 + ["ID_DSR"]

    d = desc.upper().strip()

    # Normalizações:
    #  - ' E ' -> ' ' (remove conjunções entre blocos)
    #  - 'A' range -> '-' somente quando ambos lados são dias válidos
    d = re.sub(r'\s+E\s+', ' ', d)
    d = re.sub(r'\b(SEG|TER|QUA|QUI|SEX|SAB|DOM)\s+A\s+(SEG|TER|QUA|QUI|SEX|SAB|DOM)\b',
               lambda m: f"{m.group(1)}-{m.group(2)}", d, flags=re.IGNORECASE)
    d = re.sub(r'\s+', ' ', d)

    # localizar tokens de dia e os blocos de texto entre eles
    matches = list(DAY_TOKEN_RE.finditer(d))
    jornadas = ["ID_FOLGA"] * 7
    times_to_id = {}  # reutilizar id para mesmo conjunto de horários

    for idx, m in enumerate(matches):
        token = m.group(0).upper()
        start = m.end()
        end = matches[idx+1].start() if idx+1 < len(matches) else len(d)
        block = d[start:end]

        # extrair horários no formato HH:MM
        times = re.findall(r'\d{1,2}:\d{2}', block)
        if not times:
            continue

        times_key = tuple(times)
        jid = times_to_id.get(times_key)
        if not jid:
            jid = gerar_id()
            times_to_id[times_key] = jid
            new_jornada = create_jornada_object(times)
            all_jornadas[jid] = new_jornada

        for day_idx in expand_day_token(token):
            jornadas[day_idx] = jid

    # Domingo padrão como DSR se não definido
    if jornadas[6] == "ID_FOLGA":
        jornadas[6] = "ID_DSR"
        _ensure_special_jornadas_exist(all_jornadas)

    return jornadas

def first_available(row, keys):
    """Retorna primeiro valor não vazio entre possíveis chaves do CSV (case-sensitive)."""
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    # fallback: busca key cujo nome contenha qualquer substring das keys (case-insensitive)
    for k,v in row.items():
        if v and any(k.lower().find(sub.lower()) >= 0 for sub in keys):
            return v
    return None

def create_jornada_object(times):
    """Cria o objeto de jornada com base nos horários extraídos."""
    periods = []
    batida_automatica = []
    contractual_hours = times
    
    if contractual_hours:
        periods.append({
            "TM_HORA_INICIO": "0000",
            "TM_HORA_FIM": format_time_hh_mm_to_hhmm(contractual_hours[0]),
            "DESC_TIPO_HORA": "BANCO DE HORAS"
        })

    for i in range(0, len(contractual_hours), 2):
        if i + 1 < len(contractual_hours):
            start_exp_hhmm = format_time_hh_mm_to_hhmm(contractual_hours[i])
            end_exp_hhmm = format_time_hh_mm_to_hhmm(contractual_hours[i+1])

            periods.append({
                "TM_HORA_INICIO": start_exp_hhmm,
                "TM_HORA_FIM": end_exp_hhmm,
                "DESC_TIPO_HORA": "Expediente"
            })
            
            if i + 2 < len(contractual_hours):
                interval_start_hhmm = end_exp_hhmm
                interval_end_hhmm = format_time_hh_mm_to_hhmm(contractual_hours[i+2])

                periods.append({
                    "TM_HORA_INICIO": interval_start_hhmm,
                    "TM_HORA_FIM": interval_end_hhmm,
                    "DESC_TIPO_HORA": "BANCO DE HORAS"
                })
                batida_automatica.append(interval_start_hhmm)
                batida_automatica.append(interval_end_hhmm)

    if contractual_hours and len(contractual_hours) % 2 == 0:
        periods.append({
            "TM_HORA_INICIO": format_time_hh_mm_to_hhmm(contractual_hours[-1]),
            "TM_HORA_FIM": "2400",
            "DESC_TIPO_HORA": "BANCO DE HORAS"
        })

    new_key = gerar_id()
    return {
        "NOME_JORNADA": ' | '.join(contractual_hours),
        "DESC_JORNADA": "",
        "HORAS_CONTRATUAIS": contractual_hours,
        "TRATAMENTO_EXPEDIENTE_EXTRA": "",
        "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "",
        "FL_HORA_COMPENSAVEL": "1",
        "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "",
        "FL_TRATAMENTO_CARGA_INFERIOR": "BANCO DE HORAS",
        "FL_TRATAMENTO_CARGA_SUPERIOR": "BANCO DE HORAS",
        "lose_day_by_delay": None,
        "TM_TOLERANCIA_CARGA_NEGATIVA": "0015",
        "TM_TOLERANCIA_CARGA_POSITIVA": "0015",
        "TM_INTINERE_ENTRADA": None,
        "TM_INTINERE_SAIDA": None,
        "TIPO_HORA_ADICIONAL": "BANCO DE HORAS",
        "TIPO_HORA_ADICIONAL_NOTURNO": "BANCO DE HORAS",
        "PERIODOS": periods,
        "sem_expediente": None,
        "TM_HORA_INICIO": "0000",
        "TM_TOLERANCIA_ENTRADA_ANTECIPADA": None,
        "TM_TOLERANCIA_ENTRADA_TARDIA": None,
        "TM_TOLERANCIA_SAIDA_ANTECIPADA": None,
        "TM_TOLERANCIA_SAIDA_TARDIA": None,
        "id": new_key,
        "key": new_key,
        "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""]
    }

def _ensure_special_jornadas_exist(all_jornadas_definitions):
    """Garantes que as jornadas especiais DSR e FOLGA são definidas."""
    if "ID_DSR" not in all_jornadas_definitions:
        all_jornadas_definitions["ID_DSR"] = {
            "NOME_JORNADA": "DSR",
            "DESC_JORNADA": "Descanso Semanal Remunerado",
            "HORAS_CONTRATUAIS": [],
            "TRATAMENTO_EXPEDIENTE_EXTRA": "",
            "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "",
            "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""],
            "FL_HORA_COMPENSAVEL": "1",
            "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "",
            "FL_TRATAMENTO_CARGA_INFERIOR": "BANCO DE HORAS",
            "FL_TRATAMENTO_CARGA_SUPERIOR": "BANCO DE HORAS",
            "lose_day_by_delay": None,
            "TM_TOLERANCIA_CARGA_NEGATIVA": "0015",
            "TM_TOLERANCIA_CARGA_POSITIVA": "0015",
            "TM_INTINERE_ENTRADA": None,
            "TM_INTINERE_SAIDA": None,
            "TIPO_HORA_ADICIONAL": "BANCO DE HORAS",
            "TIPO_HORA_ADICIONAL_NOTURNO": "BANCO DE HORAS",
            "PERIODOS": [],
            "sem_expediente": None,
            "TM_HORA_INICIO": "0000",
            "TM_TOLERANCIA_ENTRADA_ANTECIPADA": None,
            "TM_TOLERANCIA_ENTRADA_TARDIA": None,
            "TM_TOLERANCIA_SAIDA_ANTECIPADA": None,
            "TM_TOLERANCIA_SAIDA_TARDIA": None,
            "id": "ID_DSR",
            "key": "ID_DSR"
        }
    if "ID_FOLGA" not in all_jornadas_definitions:
        all_jornadas_definitions["ID_FOLGA"] = {
            "NOME_JORNADA": "FOLGA",
            "DESC_JORNADA": "Dia de Folga",
            "HORAS_CONTRATUAIS": [],
            "TRATAMENTO_EXPEDIENTE_EXTRA": "",
            "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "",
            "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""],
            "FL_HORA_COMPENSAVEL": "1",
            "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "",
            "FL_TRATAMENTO_CARGA_INFERIOR": "BANCO DE HORAS",
            "FL_TRATAMENTO_CARGA_SUPERIOR": "BANCO DE HORAS",
            "lose_day_by_delay": None,
            "TM_TOLERANCIA_CARGA_NEGATIVA": "0015",
            "TM_TOLERANCIA_CARGA_POSITIVA": "0015",
            "TM_INTINERE_ENTRADA": None,
            "TM_INTINERE_SAIDA": None,
            "TIPO_HORA_ADICIONAL": "BANCO DE HORAS",
            "TIPO_HORA_ADICIONAL_NOTURNO": "BANCO DE HORAS",
            "PERIODOS": [],
            "sem_expediente": None,
            "TM_HORA_INICIO": "0000",
            "TM_TOLERANCIA_ENTRADA_ANTECIPADA": None,
            "TM_TOLERANCIA_ENTRADA_TARDIA": None,
            "TM_TOLERANCIA_SAIDA_ANTECIPADA": None,
            "TM_TOLERANCIA_SAIDA_TARDIA": None,
            "id": "ID_FOLGA",
            "key": "ID_FOLGA"
        }

def processar_csv(arquivo_csv, arquivo_json):
    escalas = []
    jornadas_dict = {}

    with open(arquivo_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            nome = first_available(row, ["NOME", "NOME_DA_ESCALA", "NOME_ESCALA"])
            desc = first_available(row, ["DESC_ESCALA", "DESCRICAO_DA_ESTRUTURA", "DESCRICAO", "DESC"])
            cod = first_available(row, ["COD", "CODIGO", "CODIGO_ESCALA", "COD_ESCALA"])

            jornadas_semanais = parse_desc_escala(desc, jornadas_dict)
            carga_horaria = calculate_carga_horaria(jornadas_semanais, jornadas_dict)

            escala = {
                "NOME": nome,
                "DESC_ESCALA": desc or "",
                "COD": cod,
                "carga_horaria": carga_horaria,
                "tipo_escala": "",
                "TIPO": "SEMANAL",
                "JORNADAS": jornadas_semanais,
                "dsr": {
                    "ativo": "1",
                    "dia_completo": "1",
                    "desconto_valor_falta": "1",
                    "apuracao": {"semanal": "1"},
                },
                "TIPO_HORA_ADICIONAL": "BANCO DE HORAS",
                "TIPO_HORA_ADICIONAL_NOTURNO": "BANCO DE HORAS",
                "COD_ADICIONAL_NOTURNO": "",
                "excedente_apuracao_semanal": "",
                "deficit_apuracao_semanal": "",
                "excedente_apuracao_mensal": "",
                "deficit_apuracao_mensal": "",
                "key": gerar_id(),
                "id": gerar_id(),
            }
            escalas.append(escala)

    with open(arquivo_json, "w", encoding="utf-8") as f:
        json.dump({"escalas": escalas, "jornadas": jornadas_dict}, f, ensure_ascii=False, indent=4)

def calculate_carga_horaria(jornadas_list, all_jornadas_definitions):
    """
    Calcula a carga horária total da semana em minutos e converte para horas.
    Considera apenas os períodos de 'Expediente'.
    """
    total_minutes = 0
    for jornada_key in jornadas_list:
        if jornada_key in all_jornadas_definitions and jornada_key not in ["ID_DSR", "ID_FOLGA"]:
            jornada = all_jornadas_definitions[jornada_key]
            
            for period in jornada.get('PERIODOS', []):
                if period.get('DESC_TIPO_HORA') == 'Expediente':
                    try:
                        start_time_str = period.get('TM_HORA_INICIO')
                        end_time_str = period.get('TM_HORA_FIM')
                        
                        if not start_time_str or not end_time_str:
                            continue

                        start_hour = int(start_time_str[:2])
                        start_minute = int(start_time_str[2:])
                        end_hour = int(end_time_str[:2])
                        end_minute = int(end_time_str[2:])
                        
                        duration_minutes = (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)
                        
                        if duration_minutes < 0:
                            duration_minutes += 24 * 60
                        
                        total_minutes += duration_minutes
                    except (ValueError, TypeError):
                        continue
    
    return str(round(total_minutes / 60))

if __name__ == "__main__":
    processar_csv("MAGGI2.csv", "resultado_final_v2.json")