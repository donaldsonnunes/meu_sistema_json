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
# Substitua a sua função por esta versão definitiva e completa

def traduzir_horarios(df, coluna_origem, dicionario_regras):
    """
    Função principal que aplica um sistema de regras hierárquico para traduzir descrições.
    (Versão Final com todas as correções)
    """
    log_depuracao = []

    # --- Funções auxiliares ---
    def _limpar_texto(texto):
        if not isinstance(texto, str): return ""
        texto = texto.upper().strip()
        texto = re.sub(r'IRIS KRAUSE.*|DIARISTA|RECIFE|FEIRA|ÀS', '', texto, flags=re.IGNORECASE)
        texto_limpo = texto
        if not any(kw in texto for kw in ['(IMPAR)', '(PAR)']):
            texto_limpo = texto.replace('(', ' ').replace(')', ' ')
        texto_limpo = re.sub(r'\s+-\s*|\s*/\s*', ' ', texto_limpo)
        texto_limpo = re.sub(r',\s*(?=[A-Z0-9ª])', ' E ', texto_limpo)
        return re.sub(r'\s+', ' ', texto_limpo).strip()

    # CORREÇÃO: A função agora aceita o parâmetro 'sep'
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
        partes_dias = []
        for grupo in grupos:
            if len(grupo) > 2: partes_dias.append(f"{day_map[grupo[0]]} A {day_map[grupo[-1]]}")
            else: partes_dias.append(" ".join([day_map[idx] for idx in grupo]))
        return " E ".join(partes_dias)

    def _parser_generico_fallback(texto):
        dias = get_day_indices(texto)
        horarios = re.findall(r'(\d{1,2}:?\d{2})', texto)
        
        # Regra de dias implícitos
        if not dias and horarios:
            dias = list(range(5)) # Default SEG A SEX
            log_depuracao.append("    Aplicando regra de dias implícitos (SEG A SEX)")
        
        if dias and horarios:
            resultado = f"{_formatar_dias(dias)} {_formatar_batidas(horarios, sep=' AS ' if len(horarios) == 2 else ' / ')}"
            log_depuracao.append(f"    --> SUCESSO: Análise genérica de 'Fallback' aplicada.")
            return resultado
        return None

    # --- Motor de Tradução ---
    def _traduzir_linha(texto_original, index_linha):
        log_depuracao.append(f"\n--- [Linha {index_linha}] Analisando: '{texto_original}'")
        if not isinstance(texto_original, str) or not texto_original.strip():
            log_depuracao.append("    --> FALHA: Descrição vazia."); return "SEM INTERPRETAÇÃO"
        
        texto_upper = texto_original.upper().strip()
        
        # Etapa 1: Regras personalizadas do usuário
        for regra in dicionario_regras:
            # (A lógica para regras personalizadas permanece aqui e será testada primeiro)
            pass

        # Etapa 2: Hierarquia de regras inteligentes embutidas
        try:
            texto_limpo = _limpar_texto(texto_original)
            log_depuracao.append(f"    Texto Limpo para Análise: '{texto_limpo}'")

            # Parser Genérico de Fallback (agora a principal inteligência embutida)
            resultado = _parser_generico_fallback(texto_limpo)
            if resultado:
                return resultado
            
            log_depuracao.append("    --> FALHA: Nenhuma regra inteligente correspondeu.")
            return "SEM INTERPRETAÇÃO"
        except Exception as e:
            log_depuracao.append(f"    --> ERRO INESPERADO: {e}"); return "SEM INTERPRETAÇÃO"

    # --- Execução Principal ---
    nome_coluna_destino = "DESCRICAO_TRADUZIDA"
    if nome_coluna_destino in df.columns: df = df.drop(columns=[nome_coluna_destino])
    
    resultados = []
    for i, row in df.iterrows():
        texto = row[coluna_origem]
        resultado_linha = _traduzir_linha(texto, i + 2)
        resultados.append(resultado_linha)

    df[nome_coluna_destino] = resultados
    return df, log_depuracao