import pandas as pd
import json
import re
import uuid

def generate_key():
    """Gera uma chave hexadecimal de 24 caracteres para identificadores únicos."""
    return uuid.uuid4().hex[:24]

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

def standardize_time_range(time_range_str):
    """
    Padroniza a string de intervalo de tempo, mantendo os caracteres de tempo e batida.
    """
    if time_range_str is None:
        return ""
    # Corrige a regex para remover ':00' de todos os horários na string.
    time_range_str = re.sub(r'(\d{2}):00', r'\1', time_range_str)
    # Padroniza os separadores e remove apenas espaços extras, mantendo os espaços em torno do '|'
    standardized = re.sub(r'\s+', ' ', time_range_str.strip()).replace(' - ', 'AS').replace('-', 'AS').replace(' ÀS ', 'AS').upper()
    return standardized

def parse_time_punches(punch_times_str):
    """
    Analisa uma string contendo múltiplas batidas e retorna horários contratuais e períodos.
    """
    print(f"    --> Analisando batidas: '{punch_times_str}'")
    raw_punches = re.findall(r'(\d{2}:?\d{2})', punch_times_str)
    punches_hh_mm = [format_time_hhmm_to_hh_mm(p) for p in raw_punches]
    
    contractual_hours = punches_hh_mm
    periods = []
    batida_automatica = []

    if contractual_hours:
        periods.append({
            "TM_HORA_INICIO": "0000",
            "TM_HORA_FIM": format_time_hh_mm_to_hhmm(contractual_hours[0]),
            "DESC_TIPO_HORA": "BANCO DE HORAS"
        })

    for i in range(0, len(contractual_hours), 2):
        if i + 1 < len(contractual_hours):
            start_exp_hh_mm = contractual_hours[i]
            end_exp_hh_mm = contractual_hours[i+1]
            
            start_exp_hhmm = format_time_hh_mm_to_hhmm(start_exp_hh_mm)
            end_exp_hhmm = format_time_hh_mm_to_hhmm(end_exp_hh_mm)

            if int(start_exp_hhmm) > int(end_exp_hhmm):
                periods.append({
                    "TM_HORA_INICIO": start_exp_hhmm,
                    "TM_HORA_FIM": "2400",
                    "DESC_TIPO_HORA": "Expediente"
                })
                periods.append({
                    "TM_HORA_INICIO": "0000",
                    "TM_HORA_FIM": end_exp_hhmm,
                    "DESC_TIPO_HORA": "Expediente"
                })
            else:
                periods.append({
                    "TM_HORA_INICIO": start_exp_hhmm,
                    "TM_HORA_FIM": end_exp_hhmm,
                    "DESC_TIPO_HORA": "Expediente"
                })
            
            if i + 2 < len(contractual_hours):
                interval_start_hhmm = end_exp_hhmm
                interval_end_hhmm = format_time_hh_mm_to_hhmm(contractual_hours[i+2])

                if int(interval_start_hhmm) < int(interval_end_hhmm):
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
    
    print(f"    --> Horas Contratuais: {contractual_hours}")
    print(f"    --> Períodos: {periods}")
    print(f"    --> Batidas Automáticas: {batida_automatica}")

    return contractual_hours, periods, sorted(list(set(batida_automatica)))

def parse_simple_time_range(time_range_str):
    """
    Analisa uma string de intervalo de tempo simples.
    """
    time_range_str_std = standardize_time_range(time_range_str)
    
    contractual_hours = []
    periods = []
    batida_automatica = []
    
    print(f"    --> Analisando range simples: '{time_range_str_std}'")

    match_interval = re.match(r'(.+?)E(\d{2}:?\d{2})AS(\d{2}:?\d{2})$', time_range_str_std)
    if not match_interval:
        match_interval = re.match(r'(.+?)E(\d{2}:?\d{2})-(\d{2}:?\d{2})$', time_range_str_std)

    if match_interval:
        main_range_str = match_interval.group(1).strip()
        interval_start_raw = match_interval.group(2).strip()
        interval_end_raw = match_interval.group(3).strip()
        
        interval_start_hhmm = format_time_hh_mm_to_hhmm(interval_start_raw)
        interval_end_hhmm = format_time_hh_mm_to_hhmm(interval_end_raw)
        
        batida_automatica = [interval_start_hhmm, interval_end_hhmm]

        parts = re.split(r'AS', main_range_str)
        if len(parts) == 2:
            start_time_raw = parts[0].strip()
            end_time_raw = parts[1].strip()
            
            start_time_hhmm = format_time_hh_mm_to_hhmm(start_time_raw)
            end_time_hhmm = format_time_hh_mm_to_hhmm(end_time_raw)

            contractual_hours = [
                format_time_hhmm_to_hh_mm(start_time_hhmm),
                format_time_hhmm_to_hh_mm(interval_start_hhmm),
                format_time_hhmm_to_hh_mm(interval_end_hhmm),
                format_time_hhmm_to_hh_mm(end_time_hhmm)
            ]
            
            periods.append({"TM_HORA_INICIO": "0000", "TM_HORA_FIM": start_time_hhmm, "DESC_TIPO_HORA": "BANCO DE HORAS"})
            periods.append({"TM_HORA_INICIO": start_time_hhmm, "TM_HORA_FIM": interval_start_hhmm, "DESC_TIPO_HORA": "Expediente"})
            periods.append({"TM_HORA_INICIO": interval_start_hhmm, "TM_HORA_FIM": interval_end_hhmm, "DESC_TIPO_HORA": "BANCO DE HORAS"})
            periods.append({"TM_HORA_INICIO": interval_end_hhmm, "TM_HORA_FIM": end_time_hhmm, "DESC_TIPO_HORA": "Expediente"})
            
            if int(start_time_hhmm) > int(end_time_hhmm):
                periods[-1]["TM_HORA_FIM"] = "2400"
                periods.append({
                    "TM_HORA_INICIO": "0000",
                    "TM_HORA_FIM": end_time_hhmm,
                    "DESC_TIPO_HORA": "Expediente"
                })
                periods.append({
                    "TM_HORA_INICIO": end_time_hhmm,
                    "TM_HORA_FIM": "2400",
                    "DESC_TIPO_HORA": "BANCO DE HORAS"
                })
            else:
                 periods.append({
                    "TM_HORA_INICIO": end_time_hhmm,
                    "TM_HORA_FIM": "2400",
                    "DESC_TIPO_HORA": "BANCO DE HORAS"
                })

            return contractual_hours, periods, sorted(list(set(batida_automatica)))
    
    parts = re.split(r'AS', time_range_str_std)
    if len(parts) == 2:
        start_time_raw = parts[0].strip()
        end_time_raw = parts[1].strip()

        start_time_hhmm = format_time_hh_mm_to_hhmm(start_time_raw)
        end_time_hhmm = format_time_hh_mm_to_hhmm(end_time_raw)
        
        should_insert_default_interval = False
        if int(start_time_hhmm) < int(end_time_hhmm):
            if int(start_time_hhmm) <= 1200 and int(end_time_hhmm) >= 1300:
                should_insert_default_interval = True
        
        if should_insert_default_interval:
            default_interval_start_hhmm = "1200"
            default_interval_end_hhmm = "1300"

            contractual_hours = [
                format_time_hhmm_to_hh_mm(start_time_hhmm),
                format_time_hhmm_to_hh_mm(default_interval_start_hhmm),
                format_time_hhmm_to_hh_mm(default_interval_end_hhmm),
                format_time_hhmm_to_hh_mm(end_time_hhmm)
            ]
            batida_automatica = [default_interval_start_hhmm, default_interval_end_hhmm]

            periods = [
                {"TM_HORA_INICIO": "0000", "TM_HORA_FIM": start_time_hhmm, "DESC_TIPO_HORA": "BANCO DE HORAS"},
                {"TM_HORA_INICIO": start_time_hhmm, "TM_HORA_FIM": default_interval_start_hhmm, "DESC_TIPO_HORA": "Expediente"},
                {"TM_HORA_INICIO": default_interval_start_hhmm, "TM_HORA_FIM": default_interval_end_hhmm, "DESC_TIPO_HORA": "BANCO DE HORAS"},
                {"TM_HORA_INICIO": default_interval_end_hhmm, "TM_HORA_FIM": end_time_hhmm, "DESC_TIPO_HORA": "Expediente"}
            ]
        else:
            contractual_hours = [
                format_time_hhmm_to_hh_mm(start_time_hhmm),
                format_time_hhmm_to_hh_mm(end_time_hhmm)
            ]
            periods = [
                {"TM_HORA_INICIO": "0000", "TM_HORA_FIM": start_time_hhmm, "DESC_TIPO_HORA": "BANCO DE HORAS"},
                {"TM_HORA_INICIO": start_time_hhmm, "TM_HORA_FIM": end_time_hhmm, "DESC_TIPO_HORA": "Expediente"}
            ]

        if int(start_time_hhmm) > int(end_time_hhmm):
            periods[-1]["TM_HORA_FIM"] = "2400"
            periods.append({
                "TM_HORA_INICIO": "0000",
                "TM_HORA_FIM": end_time_hhmm,
                "DESC_TIPO_HORA": "Expediente"
            })
            periods.append({
                "TM_HORA_INICIO": end_time_hhmm,
                "TM_HORA_FIM": "2400",
                "DESC_TIPO_HORA": "BANCO DE HORAS"
            })
        else:
             periods.append({
                "TM_HORA_INICIO": end_time_hhmm,
                "TM_HORA_FIM": "2400",
                "DESC_TIPO_HORA": "BANCO DE HORAS"
            })
        return contractual_hours, periods, sorted(list(set(batida_automatica)))
    return [], [], []

def get_day_indices(day_str):
    """
    Converte uma string de dia ou dias para índices numéricos.
    """
    day_map = {
        'SEG': 0, '2ª': 0, '2A': 0, 'SEGUNDA': 0,
        'TER': 1, '3ª': 1, '3A': 1, 'TERÇA': 1,
        'QUA': 2, '4ª': 2, '4A': 2, 'QUARTA': 2,
        'QUI': 3, '5ª': 3, '5A': 3, 'QUINTA': 3,
        'SEX': 4, '6ª': 4, '6A': 4, 'SEXTA': 4,
        'SAB': 5, 'SÁBADO': 5,
        'DOM': 6, 'DOMINGO': 6
    }
    indices = []
    day_str = day_str.upper().strip()

    if 'A' in day_str and len(day_str.split()) <= 3:
        parts = day_str.split('A')
        if len(parts) == 2:
            start_day_str = parts[0].strip()
            end_day_str = parts[1].strip()
            start_index = day_map.get(start_day_str)
            end_index = day_map.get(end_day_str)
            if start_index is not None and end_index is not None:
                indices.extend(range(start_index, end_index + 1))
    elif ',' in day_str:
        for day in day_str.split(','):
            idx = day_map.get(day.strip())
            if idx is not None:
                indices.append(idx)
    else:
        idx = day_map.get(day_str)
        if idx is not None:
            indices.append(idx)
            
    return sorted(list(set(indices)))

def create_jornada_object(nome_jornada_raw):
    """
    Cria um objeto de jornada com base no nome do horário.
    """
    print(f"\n---> Chamando create_jornada_object para: '{nome_jornada_raw}'")

    if '|' in nome_jornada_raw or (len(re.findall(r'(\d{2}:?\d{2})', nome_jornada_raw.replace(' ', ''))) > 2 and 'AS' not in nome_jornada_raw.upper()):
        contractual_hours, periods, batida_automatica = parse_time_punches(nome_jornada_raw)
        nome_jornada_display = ' '.join(contractual_hours) if contractual_hours else nome_jornada_raw
    else:
        contractual_hours, periods, batida_automatica = parse_simple_time_range(nome_jornada_raw)
        if len(contractual_hours) >= 2:
            nome_jornada_display = f"{contractual_hours[0]} AS {contractual_hours[-1]}"
            if batida_automatica and not (len(batida_automatica) == 2 and batida_automatica[0] == "1200" and batida_automatica[1] == "1300"):
                nome_jornada_display += f" E {format_time_hhmm_to_hh_mm(batida_automatica[0])}-{format_time_hhmm_to_hh_mm(batida_automatica[1])}"
        else:
            nome_jornada_display = nome_jornada_raw
    
    print(f"    --> Jornada criada: {nome_jornada_display}")

    new_key = generate_key()
    return {
        "NOME_JORNADA": nome_jornada_display,
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
        "PERIODOS": [],
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

def process_schedule_description(description, jornada_mapping, all_jornadas):
    """
    Processa a descrição da escala de trabalho.
    """
    description_upper = description.upper()
    jornadas_semanais = ["ID_FOLGA"] * 7
    scale_type = "SEMANAL"

    print(f"\n\n==================================================")
    print(f"--- Analisando descrição: {description_upper} ---")
    print(f"==================================================")

    if re.search(r'12\s*X\s*36', description_upper):
        scale_type = "12X36"
        match_time = re.search(r'12\s*X\s*36\s*-\s*([0-9:\sASÀS|\-]+)', description_upper)
        time_range = match_time.group(1).strip() if match_time else "00:00 AS 00:00"
        
        standardized_time = standardize_time_range(time_range)
        
        if standardized_time not in jornada_mapping:
            new_jornada = create_jornada_object(time_range)
            jornada_mapping[standardized_time] = new_jornada['key']
            all_jornadas[new_jornada['key']] = new_jornada
        
        jornada_key = jornada_mapping[standardized_time]
        
        jornadas_semanais = [
            jornada_key, "ID_FOLGA", 
            jornada_key, "ID_FOLGA", 
            jornada_key, "ID_FOLGA", 
            "ID_DSR" 
        ]
        
        _ensure_special_jornadas_exist(all_jornadas)
        return jornadas_semanais, scale_type
    
    else:
        jornadas_semanais = ["ID_FOLGA"] * 7
        
        rules = description_upper.split(' E ')
        
        for rule in rules:
            print(f"  Regra detectada: '{rule.strip()}'")
            match = re.match(r'([A-ZÀÁÂÃÄÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÇ\s,]+)\s*(.*)', rule.strip())
            
            if match:
                days_part = match.group(1).strip()
                times_part_raw = match.group(2).strip()
                
                print(f"    > Parte dos dias: '{days_part}'")
                print(f"    > Parte dos horários: '{times_part_raw}'")

                day_indices = get_day_indices(days_part)
                
                current_jornada_key = "ID_FOLGA"
                if times_part_raw:
                    standardized_time = standardize_time_range(times_part_raw)
                    print(f"    > Horário padronizado (chave para o mapeamento): '{standardized_time}'")
                    
                    if standardized_time not in jornada_mapping:
                        new_jornada = create_jornada_object(times_part_raw)
                        jornada_mapping[standardized_time] = new_jornada['key']
                        all_jornadas[new_jornada['key']] = new_jornada
                    current_jornada_key = jornada_mapping[standardized_time]
                
                for idx in day_indices:
                    if 0 <= idx < 7:
                        jornadas_semanais[idx] = current_jornada_key
                        print(f"    -> Atribuindo jornada '{current_jornada_key}' ao dia {idx} (Seg=0, Sab=5)")

    _ensure_special_jornadas_exist(all_jornadas)
    
    if jornadas_semanais[6] == "ID_FOLGA" and scale_type == "SEMANAL":
        jornadas_semanais[6] = "ID_DSR"

    print(f"\nJornadas semanais finais: {jornadas_semanais}")
            
    return jornadas_semanais, scale_type

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
                    except (ValueError, TypeError) as ve:
                        print(f"Erro ao analisar horário no período: {period} - {ve}")
                        continue
    
    return str(round(total_minutes / 60))


def main():
    """
    Função principal que orquestra a leitura do CSV, o processamento dos dados
    e a geração do arquivo JSON de saída.
    """
    input_csv_file = 'MAGGI2.csv'
    output_json_file = 'resultado_final.json'

    try:
        df = pd.read_csv(input_csv_file)
        df.columns = [col.upper().replace(' ', '_') for col in df.columns]
        expected_cols = ['CODIGO', 'NOME_DA_ESCALA', 'DESCRICAO_DA_ESTRUTURA']
        
        if not all(col in df.columns for col in expected_cols):
             print(f"Cabeçalhos do CSV não correspondem a '{expected_cols}'. Verifique o arquivo.")
             return
        
    except Exception as e:
        print(f"Erro fatal ao ler CSV: {e}. Por favor, verifique o formato e o nome do arquivo de entrada.")
        return

    all_scales = []
    all_jornadas_definitions = {}
    jornada_mapping = {}
    used_scale_names = set()

    for index, row in df.iterrows():
        cod = str(row['CODIGO'])
        nome_escala = str(row['NOME_DA_ESCALA'])
        descricao_estrutura = str(row['DESCRICAO_DA_ESTRUTURA'])
        
        print(f"\n\n==================================================")
        print(f"Processando COD: {cod}, Nome: {nome_escala}")
        print(f"Descrição completa: {descricao_estrutura}")
        print(f"==================================================")
        
        original_nome_escala = nome_escala
        counter = 1
        while nome_escala in used_scale_names:
            nome_escala = f"{original_nome_escala} - {counter}"
            counter += 1
        used_scale_names.add(nome_escala)

        jornadas_for_scale, tipo_escala = process_schedule_description(
            descricao_estrutura, jornada_mapping, all_jornadas_definitions
        )
        
        carga_horaria = calculate_carga_horaria(jornadas_for_scale, all_jornadas_definitions)
        
        new_key = generate_key()
        scale_obj = {
            "NOME": nome_escala,
            "DESC_ESCALA": descricao_estrutura,
            "COD": cod,
            "carga_horaria": carga_horaria,
            "tipo_escala": "",
            "TIPO": tipo_escala,
            "JORNADAS": jornadas_for_scale,
            "dsr": { "ativo": "1", "dia_completo": "1", "desconto_valor_falta": "1", "apuracao": { "semanal": "1" } },
            "TIPO_HORA_ADICIONAL": "BANCO DE HORAS",
            "TIPO_HORA_ADICIONAL_NOTURNO": "BANCO DE HORAS",
            "COD_ADICIONAL_NOTURNO": "",
            "excedente_apuracao_semanal": "",
            "deficit_apuracao_semanal": "",
            "excedente_apuracao_mensal": "",
            "deficit_apuracao_mensal": "",
            "key": new_key,
            "id": new_key
        }
        all_scales.append(scale_obj)

    used_jornada_keys = set()
    for scale in all_scales:
        for jornada_key in scale['JORNADAS']:
            used_jornada_keys.add(jornada_key)

    filtered_jornadas = {
        key: all_jornadas_definitions[key] for key in used_jornada_keys
    }

    output_data = {
        "escalas": all_scales,
        "jornadas": filtered_jornadas,
        "horas_adicionais": {}
    }

    with open(output_json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(f"Arquivo '{output_json_file}' gerado com sucesso!")

if __name__ == "__main__":
    main()