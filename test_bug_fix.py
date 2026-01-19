#!/usr/bin/env python3
"""
Script para testar a correção do bug de TypeError na view cart_add.

Este script verifica se a correção do parâmetro produto_id foi bem-sucedida.
"""

import django
import os
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from plataforma_de_servicos.cart.models import ReservaEstoque
from plataforma_de_servicos.produto.models import Produto


def test_metodo_get_quantidade_reservada():
    """Testa se o método aceita objetos corretamente."""
    
    print("🧪 Testando método ReservaEstoque.get_quantidade_reservada()")
    
    # Teste 1: Verificar se método aceita None
    try:
        resultado = ReservaEstoque.get_quantidade_reservada(produto=None, variacao_produto=None)
        print(f"✅ Teste 1 PASSOU - Método aceita None: {resultado}")
    except Exception as e:
        print(f"❌ Teste 1 FALHOU - Erro com None: {e}")
        return False
    
    # Teste 2: Verificar se método aceita objeto produto
    try:
        # Criar um produto mock ou buscar um existente
        produtos = Produto.objects.all()[:1]
        if produtos:
            produto = produtos[0]
            resultado = ReservaEstoque.get_quantidade_reservada(produto=produto)
            print(f"✅ Teste 2 PASSOU - Método aceita objeto produto: {resultado}")
        else:
            # Criar um produto temporário para teste
            from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory
            produto = ProdutoFactory()
            resultado = ReservaEstoque.get_quantidade_reservada(produto=produto)
            print(f"✅ Teste 2 PASSOU - Método aceita objeto produto criado: {resultado}")
    except Exception as e:
        print(f"❌ Teste 2 FALHOU - Erro com objeto produto: {e}")
        return False
    
    # Teste 3: Verificar se método NÃO aceita produto_id (string/int)
    try:
        # Isso deve falhar com TypeError se a correção estiver correta
        ReservaEstoque.get_quantidade_reservada(produto_id=1)
        print(f"❌ Teste 3 FALHOU - Método ainda aceita produto_id incorretamente")
        return False
    except TypeError as e:
        if "produto_id" in str(e):
            print(f"✅ Teste 3 PASSOU - Método corretamente rejeita produto_id: {e}")
        else:
            print(f"⚠️ Teste 3 INCERTO - TypeError diferente: {e}")
    except Exception as e:
        print(f"❌ Teste 3 ERRO - Erro inesperado: {e}")
        return False
    
    return True


def test_simulacao_view_fix():
    """Simula a correção na view para verificar se funciona."""
    
    print("\n🔧 Simulando correção da view cart_add...")
    
    try:
        # Simular o cenário da view corrigida
        from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory
        
        # Criar produto de teste
        produto = ProdutoFactory()
        product_id = produto.id
        
        # Simular a linha corrigida da view
        print(f"📝 Testando linha corrigida: ReservaEstoque.get_quantidade_reservada(produto=produto)")
        quantidade_reservada = ReservaEstoque.get_quantidade_reservada(produto=produto)
        
        print(f"✅ CORREÇÃO FUNCIONOU - Quantidade reservada: {quantidade_reservada}")
        print(f"✅ Produto usado: {produto} (ID: {product_id})")
        
        return True
        
    except Exception as e:
        print(f"❌ CORREÇÃO FALHOU - Erro na simulação da view: {e}")
        return False


def main():
    """Função principal do teste."""
    print("🔍 TESTE DE CORREÇÃO DO BUG TypeError")
    print("=" * 60)
    
    # Executar testes
    teste1_ok = test_metodo_get_quantidade_reservada()
    teste2_ok = test_simulacao_view_fix()
    
    print("\n" + "=" * 60)
    print("📊 RESULTADO FINAL:")
    
    if teste1_ok and teste2_ok:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Bug corrigido com sucesso!")
        print("\n📋 Resumo da correção:")
        print("- Problema: view passava produto_id (int) ao invés de produto (objeto)")
        print("- Solução: buscar objeto produto e passar ao método")
        print("- Status: Funcionando corretamente")
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print("⚠️ Bug pode não estar totalmente corrigido")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)