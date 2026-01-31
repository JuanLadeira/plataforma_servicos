"""
Management command para popular o banco de dados com dados de exemplo.
Inclui categorias, produtos (carros, motos, imóveis), atributos, variações,
inventários, e ordens de compra.
"""
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from plataforma_de_servicos.corretor.models import Corretor, InteresseCompra
from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque, EstoqueItens
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.produto.models import (
    Atributo,
    Categoria,
    Produto,
    ValorAtributo,
    VariacaoProduto,
)
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.models.ordem_compra import (
    ItemOrdemCompra,
    OrdemCompra,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Popula o banco de dados com dados de exemplo (carros, motos, imóveis)"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Limpando dados antigos...")
        self._limpar_dados()

        self.stdout.write("Criando dados de exemplo...")

        # Criar superusuário
        admin, vendedor = self._criar_usuarios()

        # Criar empresa
        empresa = self._criar_empresa()

        # Criar categorias
        categorias = self._criar_categorias()

        # Criar atributos
        atributos = self._criar_atributos()

        # Criar produtos
        produtos = self._criar_produtos(categorias, atributos)

        # Criar inventários
        inventarios = self._criar_inventarios()

        # Criar movimentações de estoque
        self._criar_movimentacoes_estoque(produtos, inventarios, admin)

        # Criar ordens de compra de exemplo
        self._criar_ordens_compra(produtos, empresa, admin)

        self.stdout.write(self.style.SUCCESS("Dados de exemplo criados com sucesso!"))

    def _limpar_dados(self):
        """Limpa os dados dos modelos para evitar duplicatas."""
        OrdemCompra.objects.all().delete()
        InteresseCompra.objects.all().delete()
        EstoqueItens.objects.all().delete()
        Estoque.objects.all().delete()
        VariacaoProduto.objects.all().delete()
        Produto.objects.all().delete()
        Categoria.objects.all().delete()
        ValorAtributo.objects.all().delete()
        Atributo.objects.all().delete()
        Inventario.objects.all().delete()
        Empresa.objects.all().delete()
        Corretor.objects.filter(user__is_superuser=False).delete()
        User.objects.filter(is_superuser=False).delete()

    def _criar_usuarios(self):
        """Cria usuários de exemplo"""
        self.stdout.write("  Criando usuários...")

        admin, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={
                "name": "Administrador",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write("    Admin criado: admin@example.com / admin123")

        vendedor, created = User.objects.get_or_create(
            email="vendedor@example.com",
            defaults={
                "name": "João Vendedor",
                "is_staff": True,
            },
        )
        if created:
            vendedor.set_password("vendedor123")
            vendedor.save()
            self.stdout.write("    Vendedor criado: vendedor@example.com / vendedor123")

        Corretor.objects.get_or_create(
            user=vendedor,
            defaults={
                "nome": vendedor.name,
                "email": vendedor.email,
            },
        )

        return admin, vendedor

    def _criar_empresa(self):
        """Cria empresa de exemplo"""
        self.stdout.write("  Criando empresa...")

        empresa, _ = Empresa.objects.get_or_create(
            nome="AutoMoto Imóveis LTDA",
            defaults={
                "email": "contato@automoto.com",
            },
        )
        return empresa

    def _criar_categorias(self):
        """Cria categorias de exemplo"""
        self.stdout.write("  Criando categorias...")

        categorias = {}
        dados = [
            ("Carros", "carros"),
            ("Motos", "motos"),
            ("Imóveis", "imoveis"),
            ("Carros Usados", "carros-usados"),
            ("Motos Usadas", "motos-usadas"),
        ]

        for nome, slug in dados:
            cat, _ = Categoria.objects.get_or_create(
                categoria=nome,
                defaults={"slug": slug},
            )
            categorias[slug] = cat

        return categorias

    def _criar_atributos(self):
        """Cria atributos e valores"""
        self.stdout.write("  Criando atributos...")

        atributos = {}

        # Cor
        cor, _ = Atributo.objects.get_or_create(nome="Cor")
        cores = ["Preto", "Branco", "Prata", "Vermelho", "Azul", "Verde"]
        for c in cores:
            ValorAtributo.objects.get_or_create(atributo=cor, valor=c)
        atributos["cor"] = cor

        # Ano
        ano, _ = Atributo.objects.get_or_create(nome="Ano")
        anos = ["2020", "2021", "2022", "2023", "2024", "2025"]
        for a in anos:
            ValorAtributo.objects.get_or_create(atributo=ano, valor=a)
        atributos["ano"] = ano

        # Câmbio
        cambio, _ = Atributo.objects.get_or_create(nome="Câmbio")
        for c in ["Manual", "Automático", "CVT"]:
            ValorAtributo.objects.get_or_create(atributo=cambio, valor=c)
        atributos["cambio"] = cambio

        # Cilindrada (motos)
        cilindrada, _ = Atributo.objects.get_or_create(nome="Cilindrada")
        for c in ["150cc", "250cc", "300cc", "500cc", "600cc", "1000cc"]:
            ValorAtributo.objects.get_or_create(atributo=cilindrada, valor=c)
        atributos["cilindrada"] = cilindrada

        # Quartos (imóveis)
        quartos, _ = Atributo.objects.get_or_create(nome="Quartos")
        for q in ["1", "2", "3", "4", "5+"]:
            ValorAtributo.objects.get_or_create(atributo=quartos, valor=q)
        atributos["quartos"] = quartos

        # Tipo Imóvel
        tipo_imovel, _ = Atributo.objects.get_or_create(nome="Tipo")
        for t in ["Apartamento", "Casa", "Terreno", "Comercial"]:
            ValorAtributo.objects.get_or_create(atributo=tipo_imovel, valor=t)
        atributos["tipo_imovel"] = tipo_imovel

        return atributos

    def _criar_produtos(self, categorias, atributos):
        """Cria produtos de exemplo"""
        self.stdout.write("  Criando produtos...")

        produtos = []

        # === CARROS ===
        carros = [
            ("Toyota Corolla", Decimal("120000.00")),
            ("Honda Civic", Decimal("135000.00")),
            ("Volkswagen Golf", Decimal("95000.00")),
            ("Chevrolet Onix", Decimal("75000.00")),
            ("Ford Ka", Decimal("55000.00")),
            ("Hyundai HB20", Decimal("68000.00")),
            ("Fiat Argo", Decimal("72000.00")),
            ("Jeep Renegade", Decimal("110000.00")),
        ]

        for nome, preco in carros:
            produto, _ = Produto.objects.get_or_create(
                produto=nome,
                defaults={
                    "preco": preco,
                    "estoque": 0,
                    "categoria": categorias["carros"],
                },
            )
            produtos.append(produto)

            # Criar variações (cor + ano + câmbio)
            self._criar_variacoes_carro(produto, atributos)

        # === MOTOS ===
        motos = [
            ("Honda CB 500F", Decimal("35000.00")),
            ("Yamaha MT-03", Decimal("28000.00")),
            ("Kawasaki Ninja 400", Decimal("32000.00")),
            ("BMW G 310 R", Decimal("29000.00")),
            ("Honda CG 160", Decimal("14000.00")),
            ("Yamaha Fazer 250", Decimal("18000.00")),
        ]

        for nome, preco in motos:
            produto, _ = Produto.objects.get_or_create(
                produto=nome,
                defaults={
                    "preco": preco,
                    "estoque": 0,
                    "categoria": categorias["motos"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_moto(produto, atributos)

        # === IMÓVEIS ===
        imoveis = [
            ("Apartamento Centro - 80m²", Decimal("450000.00")),
            ("Casa Jardins - 150m²", Decimal("750000.00")),
            ("Cobertura Duplex - 200m²", Decimal("1200000.00")),
            ("Terreno Industrial - 1000m²", Decimal("500000.00")),
            ("Sala Comercial - 50m²", Decimal("280000.00")),
            ("Casa de Praia - 120m²", Decimal("650000.00")),
            ("Apartamento Compacto - 45m²", Decimal("220000.00")),
            ("Chácara - 5000m²", Decimal("380000.00")),
        ]

        for nome, preco in imoveis:
            produto, _ = Produto.objects.get_or_create(
                produto=nome,
                defaults={
                    "preco": preco,
                    "estoque": 0,
                    "categoria": categorias["imoveis"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_imovel(produto, atributos)

        return produtos

    def _criar_variacoes_carro(self, produto, atributos):
        """Cria variações para carros"""
        cores = ValorAtributo.objects.filter(atributo=atributos["cor"])[:3]
        anos = ValorAtributo.objects.filter(atributo=atributos["ano"])[:2]
        cambios = ValorAtributo.objects.filter(atributo=atributos["cambio"])[:2]

        for cor in cores:
            for ano in anos:
                for cambio in cambios:
                    variacao = VariacaoProduto.objects.create(
                        produto=produto,
                        preco=produto.preco
                        + Decimal("5000.00")
                        if cambio.valor == "Automático"
                        else produto.preco,
                        estoque=0,
                    )
                    variacao.valores.add(cor, ano, cambio)
                    variacao.gerar_sku()
                    variacao.save()

    def _criar_variacoes_moto(self, produto, atributos):
        """Cria variações para motos"""
        cores = ValorAtributo.objects.filter(atributo=atributos["cor"])[:3]
        anos = ValorAtributo.objects.filter(atributo=atributos["ano"])[:2]

        for cor in cores:
            for ano in anos:
                variacao = VariacaoProduto.objects.create(
                    produto=produto,
                    preco=produto.preco,
                    estoque=0,
                )
                variacao.valores.add(cor, ano)
                variacao.gerar_sku()
                variacao.save()

    def _criar_variacoes_imovel(self, produto, atributos):
        """Cria variações para imóveis (diferentes configurações)"""
        quartos_valores = ValorAtributo.objects.filter(atributo=atributos["quartos"])[
            :3
        ]

        for quartos in quartos_valores:
            variacao = VariacaoProduto.objects.create(
                produto=produto,
                preco=produto.preco
                + (Decimal("50000.00") * int(quartos.valor.replace("+", ""))),
                estoque=0,
            )
            variacao.valores.add(quartos)
            variacao.gerar_sku()
            variacao.save()

    def _criar_inventarios(self):
        """Cria inventários de exemplo"""
        self.stdout.write("  Criando inventários...")

        inventarios = {}

        dados = [
            ("Matriz São Paulo", True),
            ("Filial Rio de Janeiro", True),
            ("Filial Belo Horizonte", True),
            ("Showroom Premium", True),
            ("Depósito Geral", False),
        ]

        for nome, exibir in dados:
            inv, _ = Inventario.objects.get_or_create(
                nome=nome,
                defaults={"exibir_na_vitrine": exibir},
            )
            inventarios[nome] = inv

        return inventarios

    def _criar_movimentacoes_estoque(self, produtos, inventarios, funcionario):
        """Cria entradas, saídas e transferências de estoque."""
        self.stdout.write("  Criando movimentações de estoque...")

        self._criar_entradas_estoque(produtos, inventarios, funcionario)
        self._criar_saidas_estoque(produtos, inventarios, funcionario)
        self._criar_transferencias_estoque(produtos, inventarios, funcionario)

    def _criar_entradas_estoque(self, produtos, inventarios, funcionario):
        """Cria entradas de estoque para os produtos"""
        self.stdout.write("    - Criando entradas de estoque...")

        inv_principal = inventarios["Matriz São Paulo"]
        inv_deposito = inventarios["Depósito Geral"]

        # Entrada para os 10 primeiros produtos na Matriz
        for produto in produtos[:10]:
            self._criar_entrada(produto, inv_principal, funcionario, 5)

        # Entrada para os próximos 5 produtos no Depósito
        for produto in produtos[10:15]:
            self._criar_entrada(produto, inv_deposito, funcionario, 10)

    def _criar_saidas_estoque(self, produtos, inventarios, funcionario):
        """Cria saídas de estoque para alguns produtos"""
        self.stdout.write("    - Criando saídas de estoque (vendas)...")

        inv_principal = inventarios["Matriz São Paulo"]

        # Venda de 1 item dos 3 primeiros produtos que têm estoque na Matriz
        variacoes_com_estoque = VariacaoProduto.objects.filter(
            estoque__gt=1, estoque_itens__inventario=inv_principal
        ).distinct()[:3]

        if not variacoes_com_estoque:
            self.stdout.write(
                "      - Nenhuma variação com estoque suficiente na Matriz para criar saídas."
            )
            return

        for variacao in variacoes_com_estoque:
            produto = variacao.produto
            saida = Estoque.objects.create(
                funcionario=funcionario,
                movimento=Movimento.SAIDA.value,
                inventario_origem=inv_principal,
                observacao=f"Venda - {produto.produto}",
            )

            EstoqueItens.objects.create(
                estoque=saida,
                produto=produto,
                variacao=variacao,
                quantidade=1,  # Vende 1 unidade
                inventario=inv_principal,
            )
            saida.processar()
            self.stdout.write(
                f"      - Saída de 1 unidade de '{produto.produto}' ({variacao}) da Matriz."
            )

    def _criar_transferencias_estoque(self, produtos, inventarios, funcionario):
        """Cria transferências de estoque entre inventários"""
        self.stdout.write("    - Criando transferências de estoque...")

        inv_origem = inventarios["Depósito Geral"]
        inv_destino = inventarios["Filial Rio de Janeiro"]

        # Transfere 2 itens de um produto do depósito para a filial
        variacao_para_transferir = VariacaoProduto.objects.filter(
            estoque__gte=2, estoque_itens__inventario=inv_origem
        ).first()

        if variacao_para_transferir:
            produto = variacao_para_transferir.produto
            transferencia = Estoque.objects.create(
                funcionario=funcionario,
                movimento=Movimento.TRANSFERENCIA.value,
                inventario_origem=inv_origem,
                inventario_destino=inv_destino,
                observacao=f"Transferência de {inv_origem.nome} para {inv_destino.nome}",
            )

            EstoqueItens.objects.create(
                estoque=transferencia,
                produto=produto,
                variacao=variacao_para_transferir,
                quantidade=2,
                inventario=inv_origem,
            )
            transferencia.processar()
            self.stdout.write(
                f"      - Transferido 2 unidades de '{produto.produto}' ({variacao_para_transferir}) do Depósito para Filial RJ."
            )
        else:
            self.stdout.write(
                "      - Nenhuma variação com estoque suficiente no Depósito para transferir."
            )

    def _criar_entrada(self, produto, inventario, funcionario, quantidade_base):
        """Cria uma entrada de estoque para um produto e suas variações."""
        entrada = Estoque.objects.create(
            funcionario=funcionario,
            movimento=Movimento.ENTRADA.value,
            inventario_destino=inventario,
            observacao=f"Entrada inicial - {produto.produto}",
        )

        variacoes = list(produto.variacoes.all())
        if variacoes:
            # Pega até 2 variações aleatórias
            num_variacoes = min(len(variacoes), 2)
            variacoes_selecionadas = random.sample(variacoes, num_variacoes)

            for var in variacoes_selecionadas:
                qtde = random.randint(max(1, quantidade_base - 2), quantidade_base + 2)
                EstoqueItens.objects.create(
                    estoque=entrada,
                    produto=produto,
                    variacao=var,
                    quantidade=qtde,
                    inventario=inventario,
                )
        else:
            qtde = random.randint(max(1, quantidade_base - 1), quantidade_base + 1)
            EstoqueItens.objects.create(
                estoque=entrada,
                produto=produto,
                quantidade=qtde,
                inventario=inventario,
            )
        entrada.processar()
        self.stdout.write(
            f"      - Entrada de '{produto.produto}' no inventário '{inventario.nome}'."
        )

    def _criar_ordens_compra(self, produtos, empresa, usuario):
        """Cria ordens de compra de exemplo"""
        self.stdout.write("  Criando ordens de compra...")

        # Ordem pendente de aprovação
        interesse1, _ = InteresseCompra.objects.get_or_create(
            email_cliente="carlos@email.com",
            defaults={
                "nome_cliente": "Carlos Silva",
                "telefone_cliente": "11999998888",
            },
        )
        ordem1, _ = OrdemCompra.objects.get_or_create(
            interesse=interesse1,
            defaults={
                "numero": f"OC-TESTE-{interesse1.id}",
                "nome_cliente": interesse1.nome_cliente,
                "email_cliente": interesse1.email_cliente,
                "telefone_cliente": interesse1.telefone_cliente,
                "status": StatusOrdemCompra.PENDENTE_APROVACAO,
            },
        )

        # Adicionar itens
        if produtos:
            ItemOrdemCompra.objects.create(
                ordem=ordem1,
                produto=produtos[0],
                variacao=produtos[0].variacoes.first()
                if produtos[0].variacoes.exists()
                else None,
                quantidade=1,
                preco_unitario=produtos[0].preco,
            )

        # Ordem em análise
        interesse2, _ = InteresseCompra.objects.get_or_create(
            email_cliente="maria@email.com",
            defaults={
                "nome_cliente": "Maria Santos",
                "telefone_cliente": "21988887777",
            },
        )
        ordem2, _ = OrdemCompra.objects.get_or_create(
            interesse=interesse2,
            defaults={
                "numero": f"OC-TESTE-{interesse2.id}",
                "nome_cliente": interesse2.nome_cliente,
                "email_cliente": interesse2.email_cliente,
                "telefone_cliente": interesse2.telefone_cliente,
                "status": StatusOrdemCompra.PENDENTE_APROVACAO,
                "observacoes": "Aguardando aprovação de crédito",
            },
        )

        if len(produtos) > 5:
            ItemOrdemCompra.objects.create(
                ordem=ordem2,
                produto=produtos[5],
                variacao=produtos[5].variacoes.first()
                if produtos[5].variacoes.exists()
                else None,
                quantidade=1,
                preco_unitario=produtos[5].preco,
            )

        # Ordem para imóvel
        interesse3, _ = InteresseCompra.objects.get_or_create(
            email_cliente="pedro@email.com",
            defaults={
                "nome_cliente": "Pedro Oliveira",
                "telefone_cliente": "31977776666",
            },
        )
        ordem3, _ = OrdemCompra.objects.get_or_create(
            interesse=interesse3,
            defaults={
                "numero": f"OC-TESTE-{interesse3.id}",
                "nome_cliente": interesse3.nome_cliente,
                "email_cliente": interesse3.email_cliente,
                "telefone_cliente": interesse3.telefone_cliente,
                "status": StatusOrdemCompra.PENDENTE_APROVACAO,
                "observacoes": "Interesse em apartamento para investimento",
            },
        )

        if len(produtos) > 15:
            ItemOrdemCompra.objects.create(
                ordem=ordem3,
                produto=produtos[15],  # Um imóvel
                variacao=produtos[15].variacoes.first()
                if produtos[15].variacoes.exists()
                else None,
                quantidade=1,
                preco_unitario=produtos[15].preco,
            )

        self.stdout.write(f"    {OrdemCompra.objects.count()} ordens de compra criadas")
