#!/usr/bin/env python3
"""
Script para executar testes de UI com Selenium.

Este script:
1. Verifica se o ChromeDriver está disponível
2. Configura o ambiente de teste
3. Executa os testes de UI
4. Gera relatório de resultados

Uso:
    python run_ui_tests.py [--headless] [--test-pattern PATTERN]
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def check_chromedriver():
    """Verifica se o ChromeDriver está disponível."""
    try:
        result = subprocess.run(['chromedriver', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ ChromeDriver encontrado: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ ChromeDriver não encontrado!")
    print("\nPara instalar o ChromeDriver:")
    print("1. Ubuntu/Debian: sudo apt-get install chromium-chromedriver")
    print("2. macOS: brew install chromedriver")
    print("3. Windows: Baixe de https://chromedriver.chromium.org/")
    print("4. Ou use: webdriver-manager (instalado automaticamente)")
    return False


def run_tests(test_pattern=None, headless=True):
    """Executa os testes de UI."""
    # Configurar variáveis de ambiente
    env = os.environ.copy()
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings.test'
    
    if headless:
        env['SELENIUM_HEADLESS'] = '1'
    
    # Montar comando pytest
    cmd = [
        'python', '-m', 'pytest',
        'plataforma_de_servicos/cart/tests/test_ui_selenium.py',
        '-v', '-s',
        '--tb=short',
        '--no-migrations',
        '--reuse-db'
    ]
    
    if test_pattern:
        cmd.extend(['-k', test_pattern])
    
    print(f"🚀 Executando testes UI...")
    print(f"Comando: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n❌ Testes interrompidos pelo usuário")
        return 1
    except Exception as e:
        print(f"❌ Erro ao executar testes: {e}")
        return 1


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Executa testes de UI com Selenium'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Executar em modo headless (padrão: True)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Executar com interface gráfica'
    )
    parser.add_argument(
        '--test-pattern',
        help='Padrão para filtrar testes (ex: test_add_product)'
    )
    
    args = parser.parse_args()
    
    # Verificar se estamos no diretório correto
    if not Path('manage.py').exists():
        print("❌ Execute este script a partir do diretório raiz do projeto Django")
        sys.exit(1)
    
    headless = args.headless and not args.no_headless
    
    print("🧪 Configuração de Testes UI")
    print(f"Modo headless: {headless}")
    print(f"Padrão de teste: {args.test_pattern or 'Todos'}")
    print("-" * 50)
    
    # Verificar ChromeDriver (opcional, o webdriver-manager pode instalar)
    check_chromedriver()
    
    # Executar testes
    exit_code = run_tests(args.test_pattern, headless)
    
    if exit_code == 0:
        print("\n✅ Todos os testes passaram!")
    else:
        print(f"\n❌ Alguns testes falharam (código: {exit_code})")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()