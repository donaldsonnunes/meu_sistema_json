# main.py - Versão Final e Definitiva
import streamlit.web.cli as stcli
import os
import sys

def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    # Define o caminho para o seu script principal do Streamlit
    app_path = resource_path("app.py")

    # Prepara os argumentos como se estivessem vindo da linha de comando
    # Isso "engana" o Streamlit para que ele rode o script correto
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=true",
        "--server.enableCORS=false",
    ]

    # Chama a função de entrada principal do Streamlit
    sys.exit(stcli.main())