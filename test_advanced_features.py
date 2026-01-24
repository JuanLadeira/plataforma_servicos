# #!/usr/bin/env python3
# """
# Script para executar testes avançados de curto prazo:
# - Concorrência
# - Performance
# - Falhas de rede

# Este script executa os novos testes criados seguindo princípios de TDD e DDD.
# """

# import os
# import sys
# import django
# import time
# import argparse
# from django.core.management import execute_from_command_line
# from django.test.utils import get_runner
# from django.conf import settings

# # Setup Django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
# django.setup()


# class AdvancedTestRunner:
#     """Runner para testes avançados com relatórios detalhados"""

#     def __init__(self):
#         self.test_suites = {
#             'concorrencia': [
#                 'cart.tests.test_concorrencia.ConcorrenciaTest'
#             ],
#             'performance': [
#                 'cart.tests.test_performance.PerformanceTest'
#             ],
#             'network_failures': [
#                 'cart.tests.test_network_failures.NetworkFailuresTest',
#                 'payment.tests.test_network_payment_failures.PaymentNetworkFailuresTest'
#             ]
#         }

#     def run_test_suite(self, suite_name, verbosity=2):
#         """Executar uma suíte específica de testes"""
#         print(f"\n🚀 Executando suíte: {suite_name.upper()}")
#         print("=" * 60)

#         if suite_name not in self.test_suites:
#             print(f"❌ Suíte '{suite_name}' não encontrada!")
#             return False

#         start_time = time.time()

#         try:
#             # Executar testes da suíte
#             test_labels = self.test_suites[suite_name]

#             for test_label in test_labels:
#                 print(f"\n🧪 Executando: {test_label}")
#                 print("-" * 40)

#                 # Construir comando
#                 cmd = [
#                     'manage.py', 'test',
#                     test_label,
#                     '--settings=config.settings.test',
#                     f'--verbosity={verbosity}',
#                     '--keepdb'  # Manter DB para performance
#                 ]

#                 # Executar teste usando subprocess para melhor controle de memória
#                 import subprocess
#                 import gc

#                 try:
#                     result = subprocess.run(
#                         ['python'] + cmd,
#                         capture_output=True,
#                         text=True,
#                         timeout=300  # 5 minutos timeout
#                     )
#                     exit_code = result.returncode

#                     # Imprimir output se necessário
#                     if result.stdout:
#                         print(result.stdout)
#                     if result.stderr and exit_code != 0:
#                         print(result.stderr)

#                 except subprocess.TimeoutExpired:
#                     print(f"❌ Teste {test_label} expirou (timeout de 300s)")
#                     return False
#                 finally:
#                     # Forçar limpeza de memória
#                     gc.collect()

#                 if exit_code != 0:
#                     print(f"❌ Teste {test_label} falhou!")
#                     return False
#                 else:
#                     print(f"✅ Teste {test_label} passou!")

#         except Exception as e:
#             print(f"❌ Erro ao executar suíte {suite_name}: {e}")
#             return False

#         end_time = time.time()
#         duration = end_time - start_time
#         print(f"\n⏱️  Suíte {suite_name} completada em {duration:.2f}s")

#         return True

#     def run_all_tests(self, verbosity=2):
#         """Executar todas as suítes de teste"""
#         print("🎯 EXECUTANDO TODOS OS TESTES AVANÇADOS")
#         print("=" * 60)

#         start_time = time.time()
#         results = {}

#         for suite_name in self.test_suites.keys():
#             success = self.run_test_suite(suite_name, verbosity)
#             results[suite_name] = success

#         end_time = time.time()
#         total_duration = end_time - start_time

#         # Relatório final
#         print("\n" + "=" * 60)
#         print("📊 RELATÓRIO FINAL")
#         print("=" * 60)

#         passed = sum(1 for success in results.values() if success)
#         total = len(results)

#         for suite_name, success in results.items():
#             status = "✅ PASSOU" if success else "❌ FALHOU"
#             print(f"  {suite_name.upper():20} {status}")

#         print(f"\nRESUMO: {passed}/{total} suítes passaram")
#         print(f"TEMPO TOTAL: {total_duration:.2f}s")

#         if passed == total:
#             print("\n🎉 TODOS OS TESTES AVANÇADOS PASSARAM!")
#             return True
#         else:
#             print(f"\n⚠️  {total - passed} suítes falharam")
#             return False

#     def run_specific_test(self, test_path, verbosity=2):
#         """Executar um teste específico"""
#         import subprocess
#         import gc

#         print(f"\n🎯 Executando teste específico: {test_path}")

#         cmd = [
#             'python', 'manage.py', 'test',
#             test_path,
#             '--settings=config.settings.test',
#             f'--verbosity={verbosity}',
#             '--keepdb'
#         ]

#         try:
#             result = subprocess.run(
#                 cmd,
#                 capture_output=True,
#                 text=True,
#                 timeout=300  # 5 minutos timeout
#             )

#             if result.stdout:
#                 print(result.stdout)
#             if result.stderr and result.returncode != 0:
#                 print(result.stderr)

#             return result.returncode == 0

#         except subprocess.TimeoutExpired:
#             print(f"❌ Teste {test_path} expirou (timeout de 300s)")
#             return False
#         finally:
#             # Forçar limpeza de memória
#             gc.collect()


# def main():
#     parser = argparse.ArgumentParser(
#         description='Executar testes avançados (concorrência, performance, falhas de rede)'
#     )

#     parser.add_argument(
#         '--suite', '-s',
#         choices=['concorrencia', 'performance', 'network_failures', 'all'],
#         default='all',
#         help='Suíte de teste para executar (default: all)'
#     )

#     parser.add_argument(
#         '--test', '-t',
#         help='Executar teste específico (ex: cart.tests.test_concorrencia.ConcorrenciaTest.test_multiplos_usuarios)'
#     )

#     parser.add_argument(
#         '--verbosity', '-v',
#         type=int,
#         default=2,
#         choices=[0, 1, 2, 3],
#         help='Nível de verbosidade (default: 2)'
#     )

#     parser.add_argument(
#         '--benchmark', '-b',
#         action='store_true',
#         help='Executar apenas testes de performance/benchmark'
#     )

#     args = parser.parse_args()

#     runner = AdvancedTestRunner()

#     print("🧪 TESTES AVANÇADOS - TDD & DDD")
#     print("Implementações de curto prazo:")
#     print("- ⚡ Concorrência para múltiplos usuários")
#     print("- 📈 Performance para reservas em massa")
#     print("- 🔌 Falhas de rede e recuperação")
#     print()

#     if args.test:
#         # Executar teste específico
#         success = runner.run_specific_test(args.test, args.verbosity)
#         sys.exit(0 if success else 1)

#     elif args.benchmark:
#         # Executar apenas performance
#         success = runner.run_test_suite('performance', args.verbosity)
#         sys.exit(0 if success else 1)

#     elif args.suite == 'all':
#         # Executar todos
#         success = runner.run_all_tests(args.verbosity)
#         sys.exit(0 if success else 1)

#     else:
#         # Executar suíte específica
#         success = runner.run_test_suite(args.suite, args.verbosity)
#         sys.exit(0 if success else 1)


# if __name__ == '__main__':
#     main()
