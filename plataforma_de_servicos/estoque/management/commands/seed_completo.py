"""
Comando para popular o banco de dados com dados realistas para testes.

Cria dados para duas empresas com perfis distintos:
- AutoPrime: Concessionária de veículos (carros, motos) e imóveis
- AutoLitros: Mercearia/supermercado

Fluxo seguido:
1. Criar empresas
2. Criar categorias com atributos e valores
3. Criar produtos com variações (estoque zerado)
4. Criar inventários
5. Dar entrada de estoque via movimentação
6. Criar funcionários (vendedores e gerentes)
7. Criar interesses de compra (alguns convertidos, outros não)
8. Criar ordens de compra para os convertidos
9. Gerar comissões para os vendedores
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.models import EstoqueItens
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.produto.models import Atributo
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import ValorAtributo
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.users.models import Funcionario
from plataforma_de_servicos.users.models import PapelFuncionario
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.users.models import UserType
from plataforma_de_servicos.vendas.models.comissao import Comissao
from plataforma_de_servicos.vendas.models.comissao import ConfiguracaoComissao
from plataforma_de_servicos.vendas.models.comissao import StatusComissao
from plataforma_de_servicos.vendas.models.ordem_compra import ItemOrdemCompra
from plataforma_de_servicos.vendas.models.ordem_compra import OrdemCompra
from plataforma_de_servicos.vendas.models.ordem_compra import StatusOrdemCompra


# ==============================================================================
# DADOS DA AUTOPRIME (Concessionária de veículos e imóveis)
# ==============================================================================

AUTOPRIME_DATA = {
    "empresa": {
        "nome": "AutoPrime Veículos e Imóveis",
        "slug": "autoprime",
        "email": "contato@autoprime.com.br",
        "imo": "12.345.678/0001-90",
        "admin_url": "painel-gerente",
        "vendedor_url": "minha-equipe",
        "primary_color": "#1e40af",
        "secondary_color": "#3b82f6",
        "accent_color": "#f59e0b",
    },
    "categorias": [
        {
            "nome": "Carros",
            "atributos": [
                {
                    "nome": "Cor",
                    "valores": [
                        {"valor": "Branco Pérola", "preco_adicional": 2500},
                        {"valor": "Preto Onix", "preco_adicional": 2000},
                        {"valor": "Prata Metálico", "preco_adicional": 1500},
                        {"valor": "Vermelho Rubi", "preco_adicional": 3000},
                        {"valor": "Azul Steel", "preco_adicional": 2500},
                    ],
                },
                {
                    "nome": "Câmbio",
                    "valores": [
                        {"valor": "Manual 6 marchas", "preco_adicional": 0},
                        {"valor": "Automático CVT", "preco_adicional": 8000},
                        {"valor": "Automático 8 marchas", "preco_adicional": 12000},
                    ],
                },
                {
                    "nome": "Motor",
                    "valores": [
                        {"valor": "1.0 Turbo Flex", "preco_adicional": 0},
                        {"valor": "1.3 Turbo Flex", "preco_adicional": 5000},
                        {"valor": "2.0 Turbo", "preco_adicional": 15000},
                        {"valor": "Híbrido", "preco_adicional": 25000},
                    ],
                },
            ],
            "produtos": [
                {
                    "nome": "Toyota Corolla Cross XRE 2025",
                    "ncm": "87032310",
                    "preco": Decimal("185000.00"),
                    "descricao": "SUV compacto com design moderno e tecnologia de ponta.",
                },
                {
                    "nome": "Honda Civic Touring 2025",
                    "ncm": "87032310",
                    "preco": Decimal("195000.00"),
                    "descricao": "Sedã esportivo com motor turbo e acabamento premium.",
                },
                {
                    "nome": "Jeep Compass Limited 2025",
                    "ncm": "87032390",
                    "preco": Decimal("210000.00"),
                    "descricao": "SUV com tração 4x4 e recursos off-road.",
                },
                {
                    "nome": "Volkswagen T-Cross Highline 2025",
                    "ncm": "87032310",
                    "preco": Decimal("145000.00"),
                    "descricao": "SUV urbano compacto com excelente custo-benefício.",
                },
            ],
        },
        {
            "nome": "Motos",
            "atributos": [
                {
                    "nome": "Cor",
                    "valores": [
                        {"valor": "Preta", "preco_adicional": 0},
                        {"valor": "Vermelha", "preco_adicional": 500},
                        {"valor": "Azul Racing", "preco_adicional": 800},
                        {"valor": "Branca", "preco_adicional": 300},
                    ],
                },
                {
                    "nome": "Cilindrada",
                    "valores": [
                        {"valor": "150cc", "preco_adicional": 0},
                        {"valor": "250cc", "preco_adicional": 3000},
                        {"valor": "300cc", "preco_adicional": 5000},
                        {"valor": "600cc", "preco_adicional": 15000},
                        {"valor": "1000cc", "preco_adicional": 35000},
                    ],
                },
            ],
            "produtos": [
                {
                    "nome": "Honda CG 160 Titan 2025",
                    "ncm": "87112000",
                    "preco": Decimal("18500.00"),
                    "descricao": "Moto urbana econômica e confiável.",
                },
                {
                    "nome": "Yamaha Fazer 250 ABS 2025",
                    "ncm": "87112000",
                    "preco": Decimal("22000.00"),
                    "descricao": "Naked esportiva com ABS e design agressivo.",
                },
                {
                    "nome": "Honda CB 300F Twister 2025",
                    "ncm": "87112000",
                    "preco": Decimal("25000.00"),
                    "descricao": "Moto versátil para uso urbano e viagens curtas.",
                },
                {
                    "nome": "Kawasaki Ninja 650 2025",
                    "ncm": "87112000",
                    "preco": Decimal("52000.00"),
                    "descricao": "Esportiva de média cilindrada com performance excepcional.",
                },
            ],
        },
        {
            "nome": "Imóveis",
            "atributos": [
                {
                    "nome": "Tipo",
                    "valores": [
                        {"valor": "Apartamento", "preco_adicional": 0},
                        {"valor": "Casa", "preco_adicional": 50000},
                        {"valor": "Cobertura", "preco_adicional": 150000},
                        {"valor": "Terreno", "preco_adicional": -80000},
                    ],
                },
                {
                    "nome": "Quartos",
                    "valores": [
                        {"valor": "1 quarto", "preco_adicional": 0},
                        {"valor": "2 quartos", "preco_adicional": 80000},
                        {"valor": "3 quartos", "preco_adicional": 150000},
                        {"valor": "4+ quartos", "preco_adicional": 250000},
                    ],
                },
                {
                    "nome": "Localização",
                    "valores": [
                        {"valor": "Centro", "percentual_adicional": 30},
                        {"valor": "Zona Sul", "percentual_adicional": 25},
                        {"valor": "Zona Norte", "percentual_adicional": 10},
                        {"valor": "Interior", "percentual_adicional": 0},
                    ],
                },
            ],
            "produtos": [
                {
                    "nome": "Residencial Vista Park",
                    "ncm": "99999999",
                    "preco": Decimal("450000.00"),
                    "descricao": "Apartamentos com vista para o parque e área de lazer completa.",
                },
                {
                    "nome": "Condomínio Jardins Prime",
                    "ncm": "99999999",
                    "preco": Decimal("680000.00"),
                    "descricao": "Casas em condomínio fechado com segurança 24h.",
                },
                {
                    "nome": "Edifício Corporate Tower",
                    "ncm": "99999999",
                    "preco": Decimal("320000.00"),
                    "descricao": "Salas comerciais em região empresarial.",
                },
            ],
        },
    ],
    "funcionarios": [
        {
            "nome": "Carlos Silva",
            "email": "carlos.silva@autoprime.com.br",
            "papel": PapelFuncionario.GERENTE,
            "cargo": "Gerente de Vendas",
            "cpf": "123.456.789-00",
            "is_corretor": True,
        },
        {
            "nome": "Ana Souza",
            "email": "ana.souza@autoprime.com.br",
            "papel": PapelFuncionario.VENDEDOR,
            "cargo": "Consultora de Vendas",
            "cpf": "234.567.890-11",
            "is_corretor": True,
        },
        {
            "nome": "Pedro Santos",
            "email": "pedro.santos@autoprime.com.br",
            "papel": PapelFuncionario.VENDEDOR,
            "cargo": "Consultor de Vendas",
            "cpf": "345.678.901-22",
            "is_corretor": True,
        },
        {
            "nome": "Maria Oliveira",
            "email": "maria.oliveira@autoprime.com.br",
            "papel": PapelFuncionario.ADMIN,
            "cargo": "Administradora",
            "cpf": "456.789.012-33",
            "is_corretor": False,
        },
    ],
    "clientes": [
        {"nome": "João Pereira", "email": "joao.pereira@email.com", "telefone": "(11) 99999-1111"},
        {"nome": "Fernanda Lima", "email": "fernanda.lima@email.com", "telefone": "(11) 98888-2222"},
        {"nome": "Roberto Alves", "email": "roberto.alves@email.com", "telefone": "(11) 97777-3333"},
        {"nome": "Juliana Costa", "email": "juliana.costa@email.com", "telefone": "(11) 96666-4444"},
        {"nome": "Marcos Ferreira", "email": "marcos.ferreira@email.com", "telefone": "(11) 95555-5555"},
        {"nome": "Camila Rodrigues", "email": "camila.rodrigues@email.com", "telefone": "(11) 94444-6666"},
        {"nome": "Lucas Martins", "email": "lucas.martins@email.com", "telefone": "(11) 93333-7777"},
        {"nome": "Patrícia Almeida", "email": "patricia.almeida@email.com", "telefone": "(11) 92222-8888"},
    ],
}


# ==============================================================================
# DADOS DA AUTOLITROS (Mercearia/Supermercado)
# ==============================================================================

AUTOLITROS_DATA = {
    "empresa": {
        "nome": "AutoLitros Mercearia",
        "slug": "autolitros",
        "email": "contato@autolitros.com.br",
        "imo": "98.765.432/0001-10",
        "admin_url": "gerencia",
        "vendedor_url": "atendentes",
        "primary_color": "#16a34a",
        "secondary_color": "#22c55e",
        "accent_color": "#eab308",
    },
    "categorias": [
        {
            "nome": "Bebidas",
            "atributos": [
                {
                    "nome": "Tamanho",
                    "valores": [
                        {"valor": "Lata 350ml", "preco_adicional": 0},
                        {"valor": "Garrafa 600ml", "preco_adicional": 2},
                        {"valor": "Garrafa 1L", "preco_adicional": 4},
                        {"valor": "Garrafa 2L", "preco_adicional": 6},
                    ],
                },
                {
                    "nome": "Tipo",
                    "valores": [
                        {"valor": "Normal", "preco_adicional": 0},
                        {"valor": "Zero Açúcar", "preco_adicional": 0.50},
                        {"valor": "Light", "preco_adicional": 0.50},
                    ],
                },
            ],
            "produtos": [
                {
                    "nome": "Coca-Cola",
                    "ncm": "22021000",
                    "preco": Decimal("5.50"),
                    "descricao": "Refrigerante de cola tradicional.",
                },
                {
                    "nome": "Guaraná Antarctica",
                    "ncm": "22021000",
                    "preco": Decimal("4.80"),
                    "descricao": "Refrigerante de guaraná brasileiro.",
                },
                {
                    "nome": "Água Mineral Crystal",
                    "ncm": "22011000",
                    "preco": Decimal("2.50"),
                    "descricao": "Água mineral sem gás.",
                },
                {
                    "nome": "Suco Del Valle Laranja",
                    "ncm": "20099000",
                    "preco": Decimal("6.90"),
                    "descricao": "Suco de laranja natural.",
                },
            ],
        },
        {
            "nome": "Laticínios",
            "atributos": [
                {
                    "nome": "Tipo",
                    "valores": [
                        {"valor": "Integral", "preco_adicional": 0},
                        {"valor": "Desnatado", "preco_adicional": 0.30},
                        {"valor": "Sem Lactose", "preco_adicional": 1.50},
                    ],
                },
                {
                    "nome": "Tamanho",
                    "valores": [
                        {"valor": "200ml", "preco_adicional": 0},
                        {"valor": "1L", "preco_adicional": 3},
                        {"valor": "Caixa 12x1L", "preco_adicional": 35},
                    ],
                },
            ],
            "produtos": [
                {
                    "nome": "Leite Itambé",
                    "ncm": "04012010",
                    "preco": Decimal("5.20"),
                    "descricao": "Leite UHT de alta qualidade.",
                },
                {
                    "nome": "Iogurte Danone Natural",
                    "ncm": "04031000",
                    "preco": Decimal("4.50"),
                    "descricao": "Iogurte natural sem açúcar.",
                },
                {
                    "nome": "Queijo Mussarela Tirolez",
                    "ncm": "04061000",
                    "preco": Decimal("45.90"),
                    "descricao": "Queijo mussarela fatiado (kg).",
                },
            ],
        },
        {
            "nome": "Padaria",
            "atributos": [
                {
                    "nome": "Peso",
                    "valores": [
                        {"valor": "100g", "preco_adicional": 0},
                        {"valor": "250g", "preco_adicional": 3},
                        {"valor": "500g", "preco_adicional": 7},
                        {"valor": "1kg", "preco_adicional": 15},
                    ],
                },
            ],
            "produtos": [
                {
                    "nome": "Pão Francês",
                    "ncm": "19059010",
                    "preco": Decimal("1.50"),
                    "descricao": "Pão francês fresquinho (unidade).",
                },
                {
                    "nome": "Pão de Forma Seven Boys",
                    "ncm": "19059010",
                    "preco": Decimal("8.90"),
                    "descricao": "Pão de forma tradicional.",
                },
                {
                    "nome": "Croissant",
                    "ncm": "19059020",
                    "preco": Decimal("4.50"),
                    "descricao": "Croissant folhado com manteiga.",
                },
            ],
        },
        {
            "nome": "Mercearia",
            "atributos": [
                {
                    "nome": "Tamanho",
                    "valores": [
                        {"valor": "500g", "preco_adicional": 0},
                        {"valor": "1kg", "preco_adicional": 5},
                        {"valor": "5kg", "preco_adicional": 20},
                    ],
                },
            ],
            "produtos": [
                {
                    "nome": "Arroz Tio João",
                    "ncm": "10063021",
                    "preco": Decimal("8.50"),
                    "descricao": "Arroz tipo 1 agulhinha.",
                },
                {
                    "nome": "Feijão Carioca Camil",
                    "ncm": "07133319",
                    "preco": Decimal("9.90"),
                    "descricao": "Feijão carioca selecionado.",
                },
                {
                    "nome": "Açúcar União",
                    "ncm": "17019900",
                    "preco": Decimal("5.80"),
                    "descricao": "Açúcar cristal refinado.",
                },
                {
                    "nome": "Óleo de Soja Soya",
                    "ncm": "15071000",
                    "preco": Decimal("7.90"),
                    "descricao": "Óleo de soja refinado 900ml.",
                },
            ],
        },
    ],
    "funcionarios": [
        {
            "nome": "José Santos",
            "email": "jose.santos@autolitros.com.br",
            "papel": PapelFuncionario.GERENTE,
            "cargo": "Gerente da Loja",
            "cpf": "567.890.123-44",
            "is_corretor": True,
        },
        {
            "nome": "Lúcia Mendes",
            "email": "lucia.mendes@autolitros.com.br",
            "papel": PapelFuncionario.VENDEDOR,
            "cargo": "Atendente",
            "cpf": "678.901.234-55",
            "is_corretor": True,
        },
        {
            "nome": "Antônio Ferreira",
            "email": "antonio.ferreira@autolitros.com.br",
            "papel": PapelFuncionario.VENDEDOR,
            "cargo": "Atendente",
            "cpf": "789.012.345-66",
            "is_corretor": True,
        },
    ],
    "clientes": [
        {"nome": "Dona Maria", "email": "dona.maria@email.com", "telefone": "(21) 99999-1111"},
        {"nome": "Seu João", "email": "seu.joao@email.com", "telefone": "(21) 98888-2222"},
        {"nome": "Ana Clara", "email": "ana.clara@email.com", "telefone": "(21) 97777-3333"},
        {"nome": "Paulo Ricardo", "email": "paulo.ricardo@email.com", "telefone": "(21) 96666-4444"},
        {"nome": "Beatriz Souza", "email": "beatriz.souza@email.com", "telefone": "(21) 95555-5555"},
    ],
}


class Command(BaseCommand):
    help = "Popula o banco de dados com dados realistas para testes multi-tenant"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Limpa dados existentes antes de criar novos",
        )
        parser.add_argument(
            "--empresa",
            type=str,
            choices=["autoprime", "autolitros", "all"],
            default="all",
            help="Qual empresa criar dados (default: all)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self._limpar_dados()

        empresas_para_criar = options["empresa"]

        if empresas_para_criar in ["all", "autoprime"]:
            self._criar_dados_empresa(AUTOPRIME_DATA)

        if empresas_para_criar in ["all", "autolitros"]:
            self._criar_dados_empresa(AUTOLITROS_DATA)

        self.stdout.write(
            self.style.SUCCESS("\n✅ Dados de seed criados com sucesso!")
        )

    def _limpar_dados(self):
        """Remove dados existentes das empresas de teste."""
        self.stdout.write("🗑️  Limpando dados existentes...")

        empresas = Empresa.objects.filter(slug__in=["autoprime", "autolitros"])

        for empresa in empresas:
            # Deletar registros protegidos em ordem correta (de baixo para cima nas dependências)

            # 1. Comissões (dependem de OrdemCompra)
            Comissao.objects.filter(empresa=empresa).delete()

            # 2. Itens de OrdemCompra e OrdemCompra (dependem de InteresseCompra)
            ItemOrdemCompra.objects.filter(ordem__empresa=empresa).delete()
            OrdemCompra.objects.filter(empresa=empresa).delete()

            # 3. Itens de InteresseCompra e InteresseCompra
            ItemInteresse.objects.filter(interesse__empresa=empresa).delete()
            InteresseCompra.objects.filter(empresa=empresa).delete()

            # 4. Estoque e itens
            EstoqueItens.objects.filter(estoque__empresa=empresa).delete()
            Estoque.objects.filter(empresa=empresa).delete()

            # 5. Variações, Produtos, Valores, Atributos e Categorias
            VariacaoProduto.objects.filter(produto__empresa=empresa).delete()
            Produto.objects.filter(empresa=empresa).delete()
            ValorAtributo.objects.filter(atributo__categoria__empresa=empresa).delete()
            Atributo.objects.filter(categoria__empresa=empresa).delete()
            Categoria.objects.filter(empresa=empresa).delete()

            # 6. Inventários
            Inventario.objects.filter(empresa=empresa).delete()

            # 7. Funcionários e configuração de comissão
            ConfiguracaoComissao.objects.filter(empresa=empresa).delete()
            Funcionario.objects.filter(empresa=empresa).delete()

            # 8. Agora pode deletar a empresa
            empresa.delete()

        # Limpa usuários órfãos de teste
        User.objects.filter(
            email__endswith="@autoprime.com.br"
        ).delete()
        User.objects.filter(
            email__endswith="@autolitros.com.br"
        ).delete()

        self.stdout.write(self.style.SUCCESS("   Dados limpos!"))

    def _criar_dados_empresa(self, data: dict):
        """Cria todos os dados para uma empresa."""
        empresa_data = data["empresa"]
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"🏢 Criando dados para: {empresa_data['nome']}")
        self.stdout.write(f"{'='*60}")

        # 1. Criar empresa
        empresa = self._criar_empresa(empresa_data)

        # 2. Criar inventário principal
        inventario = self._criar_inventario(empresa)

        # 3. Criar categorias, atributos, valores e produtos
        produtos_criados = []
        for cat_data in data["categorias"]:
            categoria, produtos = self._criar_categoria_completa(empresa, cat_data)
            produtos_criados.extend(produtos)

        # 4. Criar entradas de estoque
        self._criar_entradas_estoque(empresa, inventario, produtos_criados)

        # 5. Criar funcionários
        funcionarios = self._criar_funcionarios(empresa, data["funcionarios"])

        # 6. Criar configuração de comissão
        self._criar_configuracao_comissao(empresa)

        # 7. Criar interesses de compra e ordens
        self._criar_interesses_e_ordens(
            empresa,
            funcionarios,
            produtos_criados,
            data["clientes"],
        )

        return empresa

    def _criar_empresa(self, data: dict) -> Empresa:
        """Cria ou atualiza uma empresa."""
        empresa, created = Empresa.objects.update_or_create(
            slug=data["slug"],
            defaults={
                "nome": data["nome"],
                "email": data["email"],
                "imo": data["imo"],
                "admin_url": data.get("admin_url", "gerentes"),
                "vendedor_url": data.get("vendedor_url", "vendedores"),
                "primary_color": data.get("primary_color", "#0ea5e9"),
                "secondary_color": data.get("secondary_color", "#64748b"),
                "accent_color": data.get("accent_color", "#f59e0b"),
            },
        )
        action = "criada" if created else "atualizada"
        self.stdout.write(f"   ✓ Empresa {action}: {empresa.nome}")
        return empresa

    def _criar_inventario(self, empresa: Empresa) -> Inventario:
        """Cria inventário principal da empresa."""
        inventario, created = Inventario.objects.update_or_create(
            empresa=empresa,
            nome="Estoque Principal",
            defaults={
                "is_ativo": True,
                "exibir_na_vitrine": True,
            },
        )
        action = "criado" if created else "atualizado"
        self.stdout.write(f"   ✓ Inventário {action}: {inventario.nome}")
        return inventario

    def _criar_categoria_completa(
        self, empresa: Empresa, cat_data: dict
    ) -> tuple[Categoria, list]:
        """Cria categoria com atributos, valores e produtos."""
        # Criar categoria
        categoria, _ = Categoria.objects.update_or_create(
            empresa=empresa,
            categoria=cat_data["nome"],
        )
        self.stdout.write(f"\n   📁 Categoria: {categoria.categoria}")

        # Criar atributos e valores
        atributos_map = {}
        for attr_data in cat_data["atributos"]:
            atributo, _ = Atributo.objects.update_or_create(
                categoria=categoria,
                nome=attr_data["nome"],
            )
            atributos_map[atributo.nome] = atributo
            self.stdout.write(f"      ├─ Atributo: {atributo.nome}")

            for val_data in attr_data["valores"]:
                valor, _ = ValorAtributo.objects.update_or_create(
                    atributo=atributo,
                    valor=val_data["valor"],
                    defaults={
                        "preco_adicional": Decimal(str(val_data.get("preco_adicional", 0))),
                        "percentual_adicional": Decimal(str(val_data.get("percentual_adicional", 0))),
                    },
                )
                self.stdout.write(f"      │  └─ {valor.valor}")

        # Criar produtos e variações
        produtos = []
        for prod_data in cat_data["produtos"]:
            produto, _ = Produto.objects.update_or_create(
                empresa=empresa,
                produto=prod_data["nome"],
                defaults={
                    "ncm": prod_data["ncm"],
                    "preco": prod_data["preco"],
                    "descricao": prod_data.get("descricao", ""),
                    "categoria": categoria,
                    "estoque": 0,  # Estoque começa zerado
                    "disponivel": True,
                },
            )
            self.stdout.write(f"      └─ Produto: {produto.produto}")

            # Criar variações combinando atributos
            variacoes = self._criar_variacoes_produto(produto, cat_data["atributos"])
            produtos.append((produto, variacoes))

        return categoria, produtos

    def _criar_variacoes_produto(
        self, produto: Produto, atributos_data: list
    ) -> list[VariacaoProduto]:
        """Cria variações de produto combinando atributos."""
        variacoes = []

        # Para simplificar, cria algumas combinações (não todas possíveis)
        # Pega até 3 valores de cada atributo
        atributos = Atributo.objects.filter(categoria=produto.categoria)

        if not atributos.exists():
            return variacoes

        # Criar combinações limitadas
        primeiro_atributo = atributos.first()
        valores_primeiro = primeiro_atributo.valores.all()[:3]

        for valor in valores_primeiro:
            # Criar variação com esse valor
            variacao = VariacaoProduto.objects.create(
                produto=produto,
                estoque=0,  # Estoque começa zerado
            )
            variacao.valores.add(valor)

            # Se houver segundo atributo, adiciona um valor dele também
            if atributos.count() > 1:
                segundo_atributo = atributos.all()[1]
                valor_segundo = segundo_atributo.valores.first()
                if valor_segundo:
                    variacao.valores.add(valor_segundo)

            # Gerar SKU
            variacao.gerar_sku()
            variacoes.append(variacao)

        self.stdout.write(f"         └─ {len(variacoes)} variações criadas")
        return variacoes

    def _criar_entradas_estoque(
        self,
        empresa: Empresa,
        inventario: Inventario,
        produtos: list,
    ):
        """Cria entradas de estoque para os produtos."""
        self.stdout.write("\n   📦 Criando entradas de estoque...")

        for produto, variacoes in produtos:
            # Criar um registro de entrada de estoque
            entrada = Estoque.objects.create(
                empresa=empresa,
                movimento=Movimento.ENTRADA.value,
                inventario_destino=inventario,
                nf=random.randint(1000, 9999),
                observacao=f"Entrada inicial - {produto.produto}",
            )

            # Se tem variações, adiciona estoque para cada variação
            if variacoes:
                for variacao in variacoes:
                    quantidade = random.randint(5, 30)
                    EstoqueItens.objects.create(
                        estoque=entrada,
                        produto=produto,
                        variacao=variacao,
                        quantidade=quantidade,
                        inventario=inventario,
                    )
            else:
                # Produto sem variações
                quantidade = random.randint(10, 50)
                EstoqueItens.objects.create(
                    estoque=entrada,
                    produto=produto,
                    quantidade=quantidade,
                    inventario=inventario,
                )

            # Processar entrada (atualiza saldos)
            entrada.processar()

        total_produtos = len(produtos)
        self.stdout.write(f"      ✓ {total_produtos} entradas de estoque processadas")

    def _criar_funcionarios(
        self, empresa: Empresa, funcionarios_data: list
    ) -> list[Funcionario]:
        """Cria funcionários da empresa."""
        self.stdout.write("\n   👥 Criando funcionários...")
        funcionarios = []

        for func_data in funcionarios_data:
            # Criar usuário
            user, user_created = User.objects.update_or_create(
                email=func_data["email"],
                defaults={
                    "name": func_data["nome"],
                    "user_type": UserType.FUNCIONARIO,
                    "empresa": empresa,
                    "is_staff": True,
                    "is_active": True,
                },
            )
            if user_created:
                user.set_password("teste123")
                user.save()

            # Criar funcionário
            funcionario, _ = Funcionario.objects.update_or_create(
                usuario=user,
                defaults={
                    "empresa": empresa,
                    "papel": func_data["papel"],
                    "cargo": func_data["cargo"],
                    "cpf": func_data["cpf"],
                    "is_corretor": func_data["is_corretor"],
                    "ativo": True,
                },
            )
            funcionarios.append(funcionario)

            papel_label = PapelFuncionario(func_data["papel"]).label
            self.stdout.write(
                f"      ✓ {funcionario.nome} ({papel_label})"
            )

        return funcionarios

    def _criar_configuracao_comissao(self, empresa: Empresa):
        """Cria configuração de comissão para a empresa."""
        config, created = ConfiguracaoComissao.objects.update_or_create(
            empresa=empresa,
            defaults={
                "percentual_padrao": Decimal("5.00"),
                "aplica_sobre_desconto": True,
            },
        )
        action = "criada" if created else "atualizada"
        self.stdout.write(f"\n   💰 Configuração de comissão {action} (5%)")

    def _criar_interesses_e_ordens(
        self,
        empresa: Empresa,
        funcionarios: list[Funcionario],
        produtos: list,
        clientes: list,
    ):
        """
        Cria interesses de compra e converte alguns em ordens.

        IMPORTANTE: As ordens de compra são criadas automaticamente via signal
        quando o status do interesse muda para CONVERTIDO. Não devemos criar
        ordens manualmente para evitar duplicação.
        """
        self.stdout.write("\n   🛒 Criando interesses de compra...")

        # Separar vendedores (corretores) dos outros
        vendedores = [f for f in funcionarios if f.is_corretor]
        if not vendedores:
            self.stdout.write("      ⚠️ Nenhum vendedor disponível")
            return

        interesses_criados = 0
        ordens_criadas = 0
        comissoes_criadas = 0

        for i, cliente in enumerate(clientes):
            # Sortear um vendedor
            vendedor = random.choice(vendedores)

            # Sortear produtos (1-3 produtos por interesse)
            num_produtos = random.randint(1, min(3, len(produtos)))
            produtos_selecionados = random.sample(produtos, num_produtos)

            # Criar interesse (status inicial é NOVO)
            interesse = InteresseCompra.objects.create(
                empresa=empresa,
                nome_cliente=cliente["nome"],
                email_cliente=cliente["email"],
                telefone_cliente=cliente["telefone"],
                mensagem=f"Interesse do cliente {cliente['nome']}",
                corretor=vendedor,
            )

            # Calcular valor total e criar itens
            valor_total = Decimal("0.00")
            for produto, variacoes in produtos_selecionados:
                # Pegar uma variação aleatória ou o produto base
                if variacoes:
                    variacao = random.choice(variacoes)
                    preco = variacao.calcular_preco_final()
                    # Formato esperado: "Atributo: Valor, Atributo2: Valor2"
                    variacao_info = ", ".join(str(v) for v in variacao.valores.all())
                else:
                    preco = produto.preco or Decimal("0.00")
                    variacao_info = ""

                quantidade = random.randint(1, 3)

                ItemInteresse.objects.create(
                    interesse=interesse,
                    produto_nome=produto.produto,
                    variacao_info=variacao_info,
                    quantidade=quantidade,
                    preco_unitario=preco,
                )
                valor_total += preco * quantidade

            interesse.valor_total = valor_total
            interesse.save()
            interesses_criados += 1

            # Decidir status do interesse
            # 50% convertidos, 30% em atendimento, 20% novos
            rand = random.random()
            if rand < 0.5:
                # Converter para ordem - o signal vai criar a OrdemCompra automaticamente
                interesse.status = StatusInteresse.CONVERTIDO
                interesse.save()

                # Buscar a ordem criada pelo signal
                interesse.refresh_from_db()
                if hasattr(interesse, "ordem_compra"):
                    ordem = interesse.ordem_compra
                    ordens_criadas += 1

                    # Avançar status da ordem aleatoriamente
                    novo_status = random.choice([
                        StatusOrdemCompra.PENDENTE_APROVACAO,
                        StatusOrdemCompra.APROVADA,
                        StatusOrdemCompra.FATURADA,
                        StatusOrdemCompra.CONCLUIDA,
                    ])
                    if novo_status != StatusOrdemCompra.PENDENTE_APROVACAO:
                        ordem.status = novo_status
                        if novo_status in [StatusOrdemCompra.APROVADA, StatusOrdemCompra.FATURADA, StatusOrdemCompra.CONCLUIDA]:
                            ordem.data_aprovacao = timezone.now()
                        ordem.save()

                    # Criar comissão para o vendedor
                    comissao = self._criar_comissao(ordem, vendedor)
                    if comissao:
                        comissoes_criadas += 1

            elif rand < 0.8:
                interesse.status = StatusInteresse.EM_ATENDIMENTO
                interesse.save()
            # else: permanece NOVO

        self.stdout.write(f"      ✓ {interesses_criados} interesses criados")
        self.stdout.write(f"      ✓ {ordens_criadas} ordens de compra (via signal)")
        self.stdout.write(f"      ✓ {comissoes_criadas} comissões geradas")

    def _criar_comissao(
        self, ordem: OrdemCompra, vendedor: Funcionario
    ) -> Comissao | None:
        """Cria comissão para o vendedor sobre a ordem."""
        # Verificar se já existe comissão para esta ordem e vendedor
        if Comissao.objects.filter(ordem=ordem, funcionario=vendedor).exists():
            return None

        # Buscar percentual configurado
        try:
            config = ConfiguracaoComissao.objects.get(empresa=ordem.empresa)
            percentual = config.percentual_padrao
        except ConfiguracaoComissao.DoesNotExist:
            percentual = Decimal("5.00")

        valor_comissao = (ordem.valor_total * percentual / Decimal("100")).quantize(
            Decimal("0.01")
        )

        # Status baseado no status da ordem
        if ordem.status == StatusOrdemCompra.CONCLUIDA:
            status = random.choice([StatusComissao.APROVADA, StatusComissao.PAGA])
        elif ordem.status == StatusOrdemCompra.FATURADA:
            status = StatusComissao.APROVADA
        else:
            status = StatusComissao.PENDENTE

        comissao = Comissao.objects.create(
            empresa=ordem.empresa,
            ordem=ordem,
            funcionario=vendedor,
            percentual=percentual,
            valor_base=ordem.valor_total,
            valor_comissao=valor_comissao,
            status=status,
        )

        if status == StatusComissao.PAGA:
            comissao.data_pagamento = timezone.now().date()
            comissao.save()

        return comissao
