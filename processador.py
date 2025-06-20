# processador.py (Versão Final e Consolidada)

import pandas as pd
import json
import re
import uuid
from datetime import datetime, timedelta

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

# =======================================================================================
# MOTOR DE TRADUÇÃO DE HORÁRIOS
# =======================================================================================
def traduzir_horarios(df, coluna_origem, regras_db):
    log_depuracao = []

    def _formatar_batidas(time_tokens, sep=" / "):
        batidas = []
        for t in time_tokens:
            n = re.sub(r'[^0-9]', '', str(t))
            if not n: continue
            if len(n) <= 2: batidas.append(f"{int(n):02d}:00")
            elif len(n) == 3: batidas.append(f"0{n[0]}:{n[1:]}")
            elif len(n) >= 4: batidas.append(f"{n[:2]}:{n[2:4]}")
        return sep.join(batidas)

    def _traduzir_linha(texto_original):
        log_depuracao.append(f"\n--- Analisando: '{texto_original}'")
        if not isinstance(texto_original, str) or not texto_original.strip():
            log_depuracao.append("    --> FALHA: Descrição vazia."); return "SEM INTERPRETAÇÃO"
        
        texto_upper = texto_original.upper().strip()

        for regra in regras_db:
            try:
                log_depuracao.append(f"    Testando Regra '{regra['nome_regra']}' (Tipo: {regra['tipo_regra']})")
                tipo_regra = regra.get('tipo_regra')

                if tipo_regra == 'EXATA':
                    if (regra.get('condicao_texto') or "").upper() == texto_upper:
                        resultado = regra['formato_saida']
                        log_depuracao.append(f"    --> SUCESSO: Regra Exata correspondeu. Resultado: '{resultado}'")
                        return resultado

                elif tipo_regra == 'DURACAO':
                    horarios = re.findall(r'(\d{1,2}:?\d{2})', texto_upper)
                    cond_duracao_str = regra.get('condicao_duracao', '') or ""
                    cond_texto = regra.get('condicao_texto', '') or ""
                    
                    duracao_corresponde = not bool(cond_duracao_str)
                    if not duracao_corresponde and len(horarios) == 2:
                        h_regra, m_regra = map(int, cond_duracao_str.split(':'))
                        timedelta_regra = timedelta(hours=h_regra, minutes=m_regra)
                        start_str, end_str = _formatar_batidas(horarios, sep=",").split(',')
                        start_dt, end_dt = datetime.strptime(start_str, "%H:%M"), datetime.strptime(end_str, "%H:%M")
                        if end_dt <= start_dt: end_dt += timedelta(days=1)
                        if abs((end_dt - start_dt) - timedelta_regra) < timedelta(minutes=1): duracao_corresponde = True
                    elif cond_duracao_str and len(horarios) != 2: continue

                    keywords = [kw.strip().upper() for kw in cond_texto.split(',') if kw.strip()]
                    keyword_corresponde = (not keywords or any(kw in texto_upper for kw in keywords))

                    if duracao_corresponde and keyword_corresponde:
                        h1 = horarios[0] if len(horarios) > 0 else ""; h2 = horarios[1] if len(horarios) > 1 else ""
                        resultado = regra['formato_saida'].replace('{h1}', h1).replace('{h2}', h2)
                        log_depuracao.append(f"    --> SUCESSO: Regra '{regra['nome_regra']}' correspondeu. Resultado: '{resultado}'")
                        return resultado

                elif tipo_regra == 'QUANTIDADE':
                    cond_qtde = int(regra.get('condicao_qtde_horarios', 0))
                    cond_sem_dia = bool(regra.get('condicao_sem_dia', False))
                    horarios = re.findall(r'(\d{1,2}:?\d{2})', texto_upper)
                    dias = get_day_indices(texto_upper)

                    if len(horarios) == cond_qtde and (not cond_sem_dia or not dias):
                        format_map = {f"h{i+1}": h for i, h in enumerate(horarios)}
                        resultado = regra['formato_saida'].format(**format_map)
                        log_depuracao.append(f"    --> SUCESSO: Regra '{regra['nome_regra']}' aplicada. Resultado: '{resultado}'")
                        return resultado
            except Exception as e:
                log_depuracao.append(f"    --> ERRO ao aplicar regra '{regra.get('nome_regra', 'Desconhecida')}': {e}"); continue
        
        log_depuracao.append("    --> FALHA: Nenhuma regra personalizada ou de padrão correspondeu.")
        return "SEM INTERPRETAÇÃO"
    
    nome_coluna_destino = "DESCRICAO_TRADUZIDA"
    if nome_coluna_destino in df.columns: df = df.drop(columns=[nome_coluna_destino])
    df[nome_coluna_destino] = df[coluna_origem].astype(str).apply(_traduzir_linha)
    return df, log_depuracao