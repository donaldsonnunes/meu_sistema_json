# teste_processador.py

import pandas as pd
import json
from processador import process_file # Importa sua função
import os

# --- Crie aqui um pequeno DataFrame com os casos mais difíceis ---
# Use exatamente os textos que estão falhando.
data = {
    'CODIGO': ['1', '3', '6', '8', '10'],
    'NOME_DA_ESCALA': [
        'Teste Sem Intervalo',
        'Teste Com Intervalo',
        'Teste 12x36 DIURNO',
        'Teste 12x36 NOTURNO',
        'Teste Semanal Complexo'
    ],
    'DESCRICAO_DA_ESTRUTURA': [
        'SEG A SEX 07:00 AS 17:00',
        'SEG A SEX 07:00 AS 17:00 E 12:00-13:00',
        '12X36 DIURNO 07:00 AS 19:00',
        '12X36 NOTURNO 19:00 AS 07:00',
        'SEG A QUI 08:00 AS 18:00 / SEX 08:00 AS 17:00'
    ]
}
df_teste = pd.DataFrame(data)

print(">>> Iniciando o teste do processador...")
print("\n>>> DataFrame de Teste:")
print(df_teste)
print("-" * 30)

# Define um caminho de saída para os resultados do teste
output_dir = "output_teste"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "resultado_teste.json")

# --- Executa a sua função `process_file` ---
# A mágica acontece aqui. Adicionamos um try/except para capturar qualquer erro.
try:
    resultado_json, escalas_desprezadas = process_file(df_teste, output_path)

    print("\n>>> Processamento concluído!")
    print("-" * 30)

    # Imprime o resultado de forma legível
    print("\n>>> JSON GERADO:")
    print(json.dumps(resultado_json, indent=4, ensure_ascii=False))
    print("-" * 30)

    # Imprime a lista de escalas que falharam
    if escalas_desprezadas:
        print("\n>>> LOG DE ESCALAS DESPREZADAS:")
        for linha in escalas_desprezadas:
            print(linha)
    else:
        print("\n>>> LOG DE ESCALAS DESPREZADAS: Nenhuma.")
        
except Exception as e:
    print(f"\n>>> OCORREU UM ERRO GRAVE DURANTE A EXECUÇÃO: {e}")
    # Esta linha é importante para capturar erros que não vimos antes
    import traceback
    traceback.print_exc()