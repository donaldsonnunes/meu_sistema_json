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
    time_hhmm_str = str(time_hhmm_str) # Garante que é string
    if len(time_hhmm_str) == 4 and time_hhmm_str.isdigit():
        return f"{time_hhmm_str[:2]}:{time_hhmm_str[2:]}"
    return time_hhmm_str # Retorna como está se não for HHMM

def format_time_hh_mm_to_hhmm(time_hh_mm_str):
    """Converte 'HH:MM' para 'HHMM'."""
    if time_hh_mm_str is None:
        return ""
    # Remove qualquer caracter que não seja dígito, garantindo apenas HHMM
    return re.sub(r'[^0-9]', '', str(time_hh_mm_str))

def standardize_time_range(time_range_str):
    """
    Padroniza a string de intervalo de tempo (ex: '08:00 AS 17:00')
    convertendo variações para um formato consistente, removendo espaços e convertendo para maiúsculas,
    substituindo '-' por 'AS' e garantindo que 'ÀS' também seja tratado.
    """
    if time_range_str is None:
        return ""
    # Remove espaços extras, converte para maiúsculas, substitui '-' e 'ÀS' por 'AS'
    return re.sub(r'\s+', '', time_range_str).replace('-', 'AS').replace('ÀS', 'AS').upper()

def parse_time_punches(punch_times_str):
    """
    Analisa uma string contendo múltiplas batidas (ex: '08:00 12:00 14:00 18:00')
    e retorna HORAS_CONTRATUAIS, PERIODOS e batida_automatica.
    Assume que batidas são pares (entrada, saída, entrada, saída...).
    """
    # Encontra todas as ocorrências de HH:MM ou HHMM e as converte para HH:MM
    raw_punches = re.findall(r'(\d{2}:?\d{2})', punch_times_str.replace(' ', ''))
    punches_hh_mm = [format_time_hhmm_to_hh_mm(p) for p in raw_punches]
    
    contractual_hours = punches_hh_mm
    periods = []
    batida_automatica = []

    # Período de Hora Extra antes da primeira batida (00:00 até a primeira batida)
    if contractual_hours:
        periods.append({
            "TM_HORA_INICIO": "0000",
            "TM_HORA_FIM": format_time_hh_mm_to_hhmm(contractual_hours[0]),
            "DESC_TIPO_HORA": "Hora Extra 50%"
        })

    # Itera sobre as batidas para criar períodos de Expediente e Hora Extra/Intervalo
    for i in range(0, len(contractual_hours), 2):
        if i + 1 < len(contractual_hours):
            start_exp_hh_mm = contractual_hours[i]
            end_exp_hh_mm = contractual_hours[i+1]
            
            start_exp_hhmm = format_time_hh_mm_to_hhmm(start_exp_hh_mm)
            end_exp_hhmm = format_time_hh_mm_to_hhmm(end_exp_hh_mm)

            # Lidar com turnos que cruzam a meia-noite (e.g., 1900-0700)
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
            
            # Período entre batidas (se for um intervalo, será Hora Extra 50%)
            if i + 2 < len(contractual_hours):
                interval_start_hhmm = end_exp_hhmm
                interval_end_hhmm = format_time_hh_mm_to_hhmm(contractual_hours[i+2])

                # Se o intervalo for de fato um intervalo de almoço/pausa (saída e reentrada)
                if int(interval_start_hhmm) < int(interval_end_hhmm): # Garante que não é um turno noturno reverso
                    periods.append({
                        "TM_HORA_INICIO": interval_start_hhmm,
                        "TM_HORA_FIM": interval_end_hhmm,
                        "DESC_TIPO_HORA": "Hora Extra 50%"
                    })
                    batida_automatica.append(interval_start_hhmm)
                    batida_automatica.append(interval_end_hhmm)
    
    # Período de Hora Extra após a última batida (última batida até 24:00)
    if contractual_hours and len(contractual_hours) % 2 == 0:
        periods.append({
            "TM_HORA_INICIO": format_time_hh_mm_to_hhmm(contractual_hours[-1]),
            "TM_HORA_FIM": "2400",
            "DESC_TIPO_HORA": "Hora Extra 50%"
        })

    return contractual_hours, periods, sorted(list(set(batida_automatica)))

def parse_simple_time_range(time_range_str):
    """
    Analisa uma string de intervalo de tempo simples (ex: '08:00 AS 17:00' ou '09:00 AS 18:00 E 12:00-13:00')
    e retorna uma lista de horas contratuais, uma lista de períodos e batidas automáticas.
    """
    time_range_str_std = standardize_time_range(time_range_str)
    
    contractual_hours = []
    periods = []
    batida_automatica = []

    # Verifica se há um intervalo de almoço explícito (ex: E 1200AS1300 ou E 1200-1300)
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
            
            periods.append({"TM_HORA_INICIO": "0000", "TM_HORA_FIM": start_time_hhmm, "DESC_TIPO_HORA": "Hora Extra 50%"})
            periods.append({"TM_HORA_INICIO": start_time_hhmm, "TM_HORA_FIM": interval_start_hhmm, "DESC_TIPO_HORA": "Expediente"})
            periods.append({"TM_HORA_INICIO": interval_start_hhmm, "TM_HORA_FIM": interval_end_hhmm, "DESC_TIPO_HORA": "Hora Extra 50%"}) # Intervalo de almoço
            periods.append({"TM_HORA_INICIO": interval_end_hhmm, "TM_HORA_FIM": end_time_hhmm, "DESC_TIPO_HORA": "Expediente"})
            
            # Lidar com turnos que cruzam a meia-noite (e.g., 1900 AS 0700)
            if int(start_time_hhmm) > int(end_time_hhmm):
                periods[-1]["TM_HORA_FIM"] = "2400" # Expediente vai até meia-noite
                periods.append({
                    "TM_HORA_INICIO": "0000",
                    "TM_HORA_FIM": end_time_hhmm,
                    "DESC_TIPO_HORA": "Expediente"
                })
                periods.append({
                    "TM_HORA_INICIO": end_time_hhmm,
                    "TM_HORA_FIM": "2400", # Hora extra do dia seguinte
                    "DESC_TIPO_HORA": "Hora Extra 50%"
                })
            else:
                 periods.append({
                    "TM_HORA_INICIO": end_time_hhmm,
                    "TM_HORA_FIM": "2400",
                    "DESC_TIPO_HORA": "Hora Extra 50%"
                })

            return contractual_hours, periods, sorted(list(set(batida_automatica)))
    
    # Se não houver intervalo explícito, tenta inferir um intervalo padrão (12:00-13:00)
    # SOMENTE se o range de trabalho abranger esse intervalo E não for um turno noturno.
    parts = re.split(r'AS', time_range_str_std)
    if len(parts) == 2:
        start_time_raw = parts[0].strip()
        end_time_raw = parts[1].strip()

        start_time_hhmm = format_time_hh_mm_to_hhmm(start_time_raw)
        end_time_hhmm = format_time_hh_mm_to_hhmm(end_time_raw)
        
        should_insert_default_interval = False
        # Condição para turnos que não cruzam a meia-noite
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
                {"TM_HORA_INICIO": "0000", "TM_HORA_FIM": start_time_hhmm, "DESC_TIPO_HORA": "Hora Extra 50%"},
                {"TM_HORA_INICIO": start_time_hhmm, "TM_HORA_FIM": default_interval_start_hhmm, "DESC_TIPO_HORA": "Expediente"},
                {"TM_HORA_INICIO": default_interval_start_hhmm, "TM_HORA_FIM": default_interval_end_hhmm, "DESC_TIPO_HORA": "Hora Extra 50%"}, # Intervalo padrão
                {"TM_HORA_INICIO": default_interval_end_hhmm, "TM_HORA_FIM": end_time_hhmm, "DESC_TIPO_HORA": "Expediente"}
            ]
        else:
            # No default interval, continuous work period or a shift that doesn't cover 12-13
            contractual_hours = [
                format_time_hhmm_to_hh_mm(start_time_hhmm),
                format_time_hhmm_to_hh_mm(end_time_hhmm)
            ]
            periods = [
                {"TM_HORA_INICIO": "0000", "TM_HORA_FIM": start_time_hhmm, "DESC_TIPO_HORA": "Hora Extra 50%"},
                {"TM_HORA_INICIO": start_time_hhmm, "TM_HORA_FIM": end_time_hhmm, "DESC_TIPO_HORA": "Expediente"}
            ]

        # Lidar com turnos que cruzam a meia-noite (e.g., 1900 AS 0700)
        if int(start_time_hhmm) > int(end_time_hhmm):
            periods[-1]["TM_HORA_FIM"] = "2400" # Último período de expediente vai até meia-noite
            periods.append({
                "TM_HORA_INICIO": "0000",
                "TM_HORA_FIM": end_time_hhmm,
                "DESC_TIPO_HORA": "Expediente"
            })
            periods.append({
                "TM_HORA_INICIO": end_time_hhmm,
                "TM_HORA_FIM": "2400",
                "DESC_TIPO_HORA": "Hora Extra 50%"
            })
        else:
             periods.append({
                "TM_HORA_INICIO": end_time_hhmm,
                "TM_HORA_FIM": "2400",
                "DESC_TIPO_HORA": "Hora Extra 50%"
            })
        return contractual_hours, periods, sorted(list(set(batida_automatica)))
    return [], [], [] # Retorna vazio se o formato não for reconhecido

def get_day_indices(day_str):
    """
    Converte uma string de dia ou dias (ex: 'SEG A QUI', '2ª,3ª,5ª')
    para índices numéricos (0=Segunda, 6=Domingo).
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

    # Ex: SEG A QUI, 2ª A 6ª
    if 'A' in day_str and len(day_str.split()) <= 3: # "DIA_INICIO A DIA_FIM"
        parts = day_str.split('A')
        if len(parts) == 2:
            start_day_str = parts[0].strip()
            end_day_str = parts[1].strip()
            start_index = day_map.get(start_day_str)
            end_index = day_map.get(end_day_str)
            if start_index is not None and end_index is not None:
                indices.extend(range(start_index, end_index + 1))
    # Ex: SEG, TER, SEX
    elif ',' in day_str:
        for day in day_str.split(','):
            idx = day_map.get(day.strip())
            if idx is not None:
                indices.append(idx)
    # Dia único (Ex: SEG, SÁBADO)
    else:
        idx = day_map.get(day_str)
        if idx is not None:
            indices.append(idx)
            
    return sorted(list(set(indices))) # Garante índices únicos e ordenados

def create_jornada_object(nome_jornada_raw):
    """
    Cria um objeto de jornada com base no nome do horário.
    Decide se o horário é um range simples ou uma sequência de batidas.
    """
    # Verifica se a string de entrada parece uma sequência de batidas (ex: "08:00 12:00 14:00 18:00")
    # A presença de mais de duas ocorrências de horário sem 'AS' sugere batidas.
    if len(re.findall(r'(\d{2}:?\d{2})', nome_jornada_raw.replace(' ', ''))) > 2 and 'AS' not in nome_jornada_raw.upper():
        contractual_hours, periods, batida_automatica = parse_time_punches(nome_jornada_raw)
        nome_jornada_display = ' '.join(contractual_hours) if contractual_hours else nome_jornada_raw
    else:
        contractual_hours, periods, batida_automatica = parse_simple_time_range(nome_jornada_raw)
        # Formata o nome da jornada para exibição
        if len(contractual_hours) >= 2:
            nome_jornada_display = f"{contractual_hours[0]} AS {contractual_hours[-1]}"
            # Se houver batidas automáticas e elas não são o padrão 12:00-13:00, adiciona ao nome de exibição
            if batida_automatica and not (len(batida_automatica) == 2 and batida_automatica[0] == "1200" and batida_automatica[1] == "1300"):
                nome_jornada_display += f" E {format_time_hhmm_to_hh_mm(batida_automatica[0])}-{format_time_hhmm_to_hh_mm(batida_automatica[1])}"
        else:
            nome_jornada_display = nome_jornada_raw


    return {
        "NOME_JORNADA": nome_jornada_display,
        "DESC_JORNADA": "",
        "HORAS_CONTRATUAIS": contractual_hours,
        "TRATAMENTO_EXPEDIENTE_EXTRA": "",
        "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "",
        "FL_HORA_COMPENSAVEL": "1",
        "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "",
        "FL_FATOR_POSTERIOR": "1",
        "FL_TRATAMENTO_CARGA_INFERIOR": "FALTA",
        "FL_TRATAMENTO_CARGA_SUPERIOR": "Hora Extra 50%",
        "PREASSINALA_SOMENTE_BATIDAS_PARES": bool(batida_automatica), # True se houver batidas automáticas
        "batida_automatica": batida_automatica,
        "PERIODOS": periods,
        "key": generate_key(),
        "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""] # Mantido como vazio conforme exemplo original
    }

def process_schedule_description(description, jornada_mapping, all_jornadas):
    """
    Processa a descrição da escala de trabalho para determinar o array de jornadas
    para a semana e o tipo da escala.
    Atualiza os dicionários de mapeamento e definições de jornadas.
    """
    description_upper = description.upper() # Use this for case-insensitive checks
    jornadas_semanais = ["ID_FOLGA"] * 7 # Inicializa com "ID_FOLGA" para todos os dias
    scale_type = "SEMANAL" # Default type

    # --- Start of Cycle Fixed Scale Detection ---
    # Verifica palavras-chave de ciclo fixo primeiro e retorna para evitar conflitos
    if re.search(r'12\s*X\s*36', description_upper): # Catches "12X36", "12 X 36", etc.
        scale_type = "12X36"
        # Regex para extrair o horário após "12 X 36 -" ou "12X36 -"
        match_time = re.search(r'12\s*X\s*36\s*-\s*([0-9:\sASÀS-]+)', description_upper)
        time_range = match_time.group(1).strip() if match_time else "00:00 AS 00:00" # Default if not found
        
        standardized_time = standardize_time_range(time_range)
        
        if standardized_time not in jornada_mapping:
            new_jornada = create_jornada_object(time_range)
            jornada_mapping[standardized_time] = new_jornada['key']
            all_jornadas[new_jornada['key']] = new_jornada
        
        jornada_key = jornada_mapping[standardized_time]
        
        # Padrão para 12x36: dia de trabalho e dia de folga alternados.
        # Considerando um ciclo que se repete ao longo da semana.
        # Exemplo: [trabalho, folga, trabalho, folga, trabalho, folga, DSR (se domingo for folga)]
        # Para 7 dias, um padrão comum é 3 dias de trabalho e 4 de folga, ou 4 de trabalho e 3 de folga.
        # A jornada_key é para o dia de trabalho 12h.
        jornadas_semanais = [
            jornada_key, "ID_FOLGA", # Dia 1: Trabalho, Dia 2: Folga
            jornada_key, "ID_FOLGA", # Dia 3: Trabalho, Dia 4: Folga
            jornada_key, "ID_FOLGA", # Dia 5: Trabalho, Dia 6: Folga
            "ID_DSR" # Dia 7: Domingo como DSR
        ]
        
        # Garante que DSR e FOLGA existem em all_jornadas_definitions
        _ensure_special_jornadas_exist(all_jornadas)
        return jornadas_semanais, scale_type

    elif re.search(r'6\s*X\s*1', description_upper): # Catches "6X1", "6 X 1", etc.
        scale_type = "6X1"
        # Regex para extrair o horário após "6X1 -"
        match_time = re.search(r'6\s*X\s*1\s*-\s*([0-9:\sASÀS-]+)', description_upper)
        time_range = match_time.group(1).strip() if match_time else "00:00 AS 00:00" # Default if not found
        
        standardized_time = standardize_time_range(time_range)
        
        if standardized_time not in jornada_mapping:
            new_jornada = create_jornada_object(time_range)
            jornada_mapping[standardized_time] = new_jornada['key']
            all_jornadas[new_jornada['key']] = new_jornada
        
        jornada_key = jornada_mapping[standardized_time]
        jornadas_semanais = [jornada_key] * 6 + ["ID_DSR"] # 6 dias de trabalho, 1 DSR
        
        # Garante que DSR e FOLGA existem
        _ensure_special_jornadas_exist(all_jornadas)
        return jornadas_semanais, scale_type
    # --- End of Cycle Fixed Scale Detection ---
    
    else: # Escala SEMANAL
        # Regex para encontrar segmentos de "DIAS HORÁRIOS" dentro da descrição.
        # Esta regex busca por um bloco de dias, seguido por um separador opcional (hífen ou espaço),
        # e depois uma parte que se assemelha a horários.
        # Ela é projetada para ser flexível e capturar múltiplos blocos "DIAS HORÁRIOS"
        # mesmo sem um "E" explícito entre eles, como em "SEG A QUI 08:00 AS 18:00 SEX 08:00:00 AS 17:00:00"
        segment_parser_regex = re.compile(
            r'([A-ZÀÁÂÃÄÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÇ\s,]+?)'  # Group 1: Dias (non-greedy)
            r'(?:\s*-\s*|\s+)'  # Separador opcional ' - ' ou apenas espaço
            r'('  # Início do Grupo 2: Parte dos horários
            r'(?:\d{2}:?\d{2}'  # Início de um horário (HHMM ou HH:MM)
            r'(?:\s*(?:AS|ÀS|\-)?\s*\d{2}:?\d{2})*'  # Continuação de um range ou mais batidas
            r')' # Fecha o grupo da sequência de horários
            r'(?:\s+E\s+\d{2}:?\d{2}(?:AS|\-)\d{2}:?\d{2})?' # Possível intervalo explícito no final
            r')' # Fim do Grupo 2: Parte dos horários
        )
        
        # Inicializa jornadas semanais com FOLGA para todos os 7 dias
        jornadas_semanais = ["ID_FOLGA"] * 7
        
        # Encontra todas as correspondências na descrição completa da escala
        last_match_end = 0
        
        for match in segment_parser_regex.finditer(description_upper):
            days_part = match.group(1).strip()
            times_part_raw = match.group(2).strip()
            
            # Debug: print(f"  Captured Segment: Days='{days_part}', Times='{times_part_raw}'")

            day_indices = get_day_indices(days_part) # Converte a parte dos dias em índices numéricos
            
            # Decide se a jornada é de FOLGA ou uma jornada de trabalho com base nos horários
            # Se a parte dos horários capturada for vazia, ou não parecer um horário válido,
            # então é um dia de FOLGA.
            if not times_part_raw or not re.search(r'\d{2}:?\d{2}', times_part_raw): 
                current_jornada_key = "ID_FOLGA"
            else:
                standardized_time = standardize_time_range(times_part_raw)
                if standardized_time not in jornada_mapping:
                    # Cria uma nova jornada se não existir mapeamento para esse horário
                    new_jornada = create_jornada_object(times_part_raw)
                    jornada_mapping[standardized_time] = new_jornada['key']
                    all_jornadas[new_jornada['key']] = new_jornada
                current_jornada_key = jornada_mapping[standardized_time]
            
            # Atribui a chave da jornada aos dias correspondentes na semana
            for idx in day_indices:
                if 0 <= idx < 7: # Garante que o índice esteja dentro do range de 0 a 6
                    jornadas_semanais[idx] = current_jornada_key
            
            last_match_end = match.end() # Atualiza o fim da última correspondência

        # TRATAMENTO PARA DIAS NO FIM DA STRING QUE PODEM SER FOLGA/DSR SEM HORÁRIO
        # Verifica se há texto remanescente após o último match.
        remaining_description = description_upper[last_match_end:].strip()
        if remaining_description:
            # Tenta encontrar padrões de dias sem horários (ex: "SABADO", "DOMINGO")
            remaining_days_match = re.search(r'([A-ZÀÁÂÃÄÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÇ\s,]+)', remaining_description)
            if remaining_days_match:
                days_part_remaining = remaining_days_match.group(1).strip()
                day_indices_remaining = get_day_indices(days_part_remaining)
                for idx in day_indices_remaining:
                    if 0 <= idx < 7 and jornadas_semanais[idx] == "ID_FOLGA": # Só preenche se já não tiver uma jornada
                        jornadas_semanais[idx] = "ID_FOLGA" # Mantém como ID_FOLGA explicitamente
                        # Debug: print(f"  Remaining Day as FOLGA: Day={idx}, Desc='{days_part_remaining}'")


    # Garante que as jornadas especiais DSR e FOLGA existam em all_jornadas_definitions
    _ensure_special_jornadas_exist(all_jornadas)
    
    # Se o Domingo (índice 6) ainda for "ID_FOLGA" (e não foi preenchido por uma regra de trabalho), preenche com "ID_DSR"
    # Esta é a regra final para o domingo, garantindo que ele não fique como FOLGA se a escala for SEMANAL.
    if jornadas_semanais[6] == "ID_FOLGA" and scale_type == "SEMANAL":
        jornadas_semanais[6] = "ID_DSR"
            
    return jornadas_semanais, scale_type

def _ensure_special_jornadas_exist(all_jornadas_definitions):
    """Garantes que as jornadas especiais DSR e FOLGA são definidas."""
    if "ID_DSR" not in all_jornadas_definitions:
        all_jornadas_definitions["ID_DSR"] = {
            "NOME_JORNADA": "DSR",
            "DESC_JORNADA": "Descanso Semanal Remunerado",
            "HORAS_CONTRATUAIS": [], "TRATAMENTO_EXPEDIENTE_EXTRA": "",
            "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "", "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""],
            "FL_HORA_COMPENSAVEL": "1", "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "", "FL_FATOR_POSTERIOR": "1",
            "FL_TRATAMENTO_CARGA_INFERIOR": "FALTA", "FL_TRATAMENTO_CARGA_SUPERIOR": "Hora Extra 50%",
            "PREASSINALA_SOMENTE_BATIDAS_PARES": False, "batida_automatica": [], "PERIODOS": [],
            "key": "ID_DSR" # Chave fixa para o DSR
        }
    if "ID_FOLGA" not in all_jornadas_definitions:
        all_jornadas_definitions["ID_FOLGA"] = {
            "NOME_JORNADA": "FOLGA",
            "DESC_JORNADA": "Dia de Folga",
            "HORAS_CONTRATUAIS": [], "TRATAMENTO_EXPEDIENTE_EXTRA": "",
            "TRATAMENTO_ADICIONAL_PARA_PERIODO_DO_DIA": "", "HORAS_CONTRATUAIS_INTERVALO_EXTRA": ["", ""],
            "FL_HORA_COMPENSAVEL": "1", "FL_ADICIONAL_NOTURNO_SOBRE_EXTRA": "", "FL_FATOR_POSTERIOR": "1",
            "FL_TRATAMENTO_CARGA_INFERIOR": "FALTA", "FL_TRATAMENTO_CARGA_SUPERIOR": "Hora Extra 50%",
            "PREASSINALA_SOMENTE_BATIDAS_PARES": False, "batida_automatica": [], "PERIODOS": [],
            "key": "ID_FOLGA" # Chave fixa para FOLGA
        }


def calculate_carga_horaria(jornadas_list, all_jornadas_definitions):
    """
    Calcula a carga horária total da semana em minutos e converte para horas.
    Considera apenas os períodos de 'Expediente'.
    """
    total_minutes = 0
    for jornada_key in jornadas_list:
        # Apenas calcula se a chave da jornada é uma jornada válida (não DSR ou FOLGA)
        if jornada_key in all_jornadas_definitions and jornada_key not in ["ID_DSR", "ID_FOLGA"]:
            jornada = all_jornadas_definitions[jornada_key]
            
            for period in jornada.get('PERIODOS', []):
                if period.get('DESC_TIPO_HORA') == 'Expediente':
                    try:
                        # Converte 'HHMM' para minutos
                        start_time_str = period['TM_HORA_INICIO']
                        end_time_str = period['TM_HORA_FIM']

                        if not start_time_str or not end_time_str:
                            continue # Pula se o horário estiver faltando ou mal formatado

                        start_hour = int(start_time_str[:2])
                        start_minute = int(start_time_str[2:])
                        end_hour = int(end_time_str[:2])
                        end_minute = int(end_time_str[2:])
                        
                        duration_minutes = (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)
                        
                        # Lidar com períodos que cruzam a meia-noite (duração negativa)
                        if duration_minutes < 0:
                            duration_minutes += 24 * 60 # Adiciona 24 horas em minutos para turnos noturnos
                        
                        total_minutes += duration_minutes
                    except ValueError as ve:
                        print(f"Erro ao analisar horário no período: {period} - {ve}")
                        continue
    
    # Retorna a carga horária em horas (arredondado para o inteiro mais próximo)
    return str(round(total_minutes / 60))


def main():
    """
    Função principal que orquestra a leitura do CSV, o processamento dos dados
    e a geração do arquivo JSON de saída.
    """
    input_csv_file = 'escalas_para_processar.csv'
    output_json_file = 'resultado_final.json'

    try:
        # Tenta ler o CSV assumindo que a primeira linha é o cabeçalho
        df = pd.read_csv(input_csv_file)
        # Renomeia as colunas para um acesso mais fácil, ignorando maiúsculas/minúsculas
        df.columns = [col.upper().replace(' ', '_') for col in df.columns]
        # Garante que as colunas esperadas existam
        if not all(col in df.columns for col in ['CODIGO', 'NOME_DA_ESCALA', 'DESCRICAO_DA_ESTRUTURA']):
             raise ValueError("Cabeçalhos do CSV não correspondem ao esperado: 'CODIGO', 'NOME DA ESCALA', 'DESCRIÇÃO DA ESTRUTURA'.")
    except Exception as e:
        print(f"Erro ao ler CSV com cabeçalho: {e}. Tentando ler sem cabeçalho.")
        try:
            # Se a leitura com cabeçalho falhar, tenta ler sem cabeçalho
            df = pd.read_csv(input_csv_file, header=None, names=['CODIGO', 'NOME_DA_ESCALA', 'DESCRICAO_DA_ESTRUTURA'])
        except Exception as e:
            print(f"Erro fatal ao ler CSV sem cabeçalho: {e}. Por favor, verifique o formato do arquivo de entrada.")
            return

    all_scales = []
    all_jornadas_definitions = {} # Dicionário para armazenar todas as definições de jornadas por key
    jornada_mapping = {} # Mapeia string de horário padronizada para a key da jornada (para evitar duplicatas)

    for index, row in df.iterrows():
        cod = str(row['CODIGO'])
        nome_escala = str(row['NOME_DA_ESCALA'])
        descricao_estrutura = str(row['DESCRICAO_DA_ESTRUTURA'])
        
        # Debug: print(f"Processing scale: COD={cod}, NOME='{nome_escala}', DESC='{descricao_estrutura}'")

        jornadas_for_scale, tipo_escala = process_schedule_description(
            descricao_estrutura, jornada_mapping, all_jornadas_definitions
        )
        
        carga_horaria = calculate_carga_horaria(jornadas_for_scale, all_jornadas_definitions)

        scale_obj = {
            "NOME": nome_escala,
            "DESC_ESCALA": descricao_estrutura, # Mantém a descrição original aqui
            "COD": cod,
            "carga_horaria": carga_horaria,
            "tipo_escala": "", # Este campo pode ser populado com lógica adicional se houver tipos além de SEMANAL, 6X1, 12X36
            "TIPO": tipo_escala,
            "JORNADAS": jornadas_for_scale,
            "dsr": { "ativo": "1", "dia_completo": "1", "desconto_valor_falta": "1", "apuracao": { "semanal": "1" } },
            "TIPO_HORA_ADICIONAL": "",
            "TIPO_HORA_ADICIONAL_NOTURNO": "",
            "COD_ADICIONAL_NOTURNO": "",
            "excedente_apuracao_semanal": "",
            "deficit_apuracao_semanal": "",
            "excedente_apuracao_mensal": "",
            "deficit_apuracao_mensal": "",
            "key": generate_key()
        }
        all_scales.append(scale_obj)

    # Filtra as jornadas para incluir apenas aquelas que foram efetivamente usadas
    used_jornada_keys = set()
    for scale in all_scales:
        for jornada_key in scale['JORNADAS']:
            used_jornada_keys.add(jornada_key)

    filtered_jornadas = {
        key: value for key, value in all_jornadas_definitions.items()
        if key in used_jornada_keys
    }

    output_data = {
        "escalas": all_scales,
        "jornadas": list(filtered_jornadas.values()), # Converte para lista de objetos JSON
        "horas_adicionais": [] # Assumindo que este bloco estará vazio com base no prompt
    }

    with open(output_json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(f"Arquivo '{output_json_file}' gerado com sucesso!")

if __name__ == "__main__":
    main()
