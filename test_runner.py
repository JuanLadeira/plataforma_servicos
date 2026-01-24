# #!/usr/bin/env python
# """
# Script para executar todos os testes das novas funcionalidades implementadas.
# """
# import os
# import sys
# import django
# from django.conf import settings
# from django.test.utils import get_runner

# if __name__ == "__main__":
#     import gc
#     from django.db import connection

#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
#     django.setup()

#     try:
#         # Testes específicos das novas funcionalidades
#         test_modules = [
#             'cart.tests.test_reserva_estoque',
#             'cart.tests.test_cart_reservas',
#             'cart.tests.test_cart_views',
#             'estoque.tests.test_estoque_service',
#             'estoque.tests.test_estoque_model',
#             'payment.tests.test_payment_estoque_integration',
#         ]

#         TestRunner = get_runner(settings)
#         test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)

#         print("🚀 Executando testes das novas funcionalidades...")
#         print("📋 Módulos sendo testados:")
#         for module in test_modules:
#             print(f"  - {module}")
#         print()

#         failures = test_runner.run_tests(test_modules)

#         if failures:
#             print(f"❌ {failures} teste(s) falharam")
#             sys.exit(1)
#         else:
#             print("✅ Todos os testes passaram com sucesso!")
#             print()
#             print("📊 Funcionalidades testadas:")
#             print("  ✓ Sistema de reservas de estoque")
#             print("  ✓ Validação de estoque no carrinho")
#             print("  ✓ Integração carrinho + estoque + pagamento")
#             print("  ✓ Saída automática de estoque por pedidos")
#             print("  ✓ Logs e rastreabilidade de origem de saída")
#             print("  ✓ Redirecionamento automático para carrinho")
#             sys.exit(0)

#     finally:
#         # Limpeza de conexões e memória
#         try:
#             connection.close()
#         except:
#             pass
#         gc.collect()
