"""
Comando para popular produtos de teste para cada empresa.

Uso:
    python manage.py seed_produtos                    # Popula todas as empresas
    python manage.py seed_produtos --empresa=autoprime  # Apenas uma empresa
    python manage.py seed_produtos --clear            # Limpa e repopula
"""
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.produto.models import Categoria, Produto, Atributo, ValorAtributo, VariacaoProduto
from plataforma_de_servicos.inventario.models import Inventario, InventarioSaldo


# Dados de produtos por empresa
PRODUTOS_POR_EMPRESA = {
    "autoprime": {
        "nome_display": "AutoPrime Veículos e Imóveis",
        "admin_title": "AutoPrime Admin",
        "admin_subtitle": "Gestão de Veículos e Imóveis",
        "primary_color": "#1e40af",  # Azul escuro
        "secondary_color": "#475569",
        "accent_color": "#eab308",  # Amarelo dourado
        "welcome_message": "Bem-vindo ao painel de gestão da AutoPrime! Aqui você gerencia veículos e imóveis premium.",
        "categorias": [
            {
                "nome": "Carros",
                "produtos": [
                    {
                        "nome": "Honda Civic 2024",
                        "descricao": "Sedan executivo com motor 2.0 turbo, 173cv. Câmbio CVT, ar digital, central multimídia.",
                        "preco": Decimal("159900.00"),
                        "atributos": {
                            "Cor": [
                                ("Preto Perolizado", Decimal("0"), Decimal("0")),
                                ("Branco Pérola", Decimal("2500"), Decimal("0")),
                                ("Prata Metálico", Decimal("1500"), Decimal("0")),
                            ],
                            "Motor": [
                                ("2.0 Turbo", Decimal("0"), Decimal("0")),
                                ("1.5 Turbo", Decimal("-8000"), Decimal("0")),
                            ],
                        },
                    },
                    {
                        "nome": "Toyota Corolla Cross 2024",
                        "descricao": "SUV híbrido flex, 122cv combinados. Tração 4x4, 7 airbags, sensor de estacionamento.",
                        "preco": Decimal("189900.00"),
                        "atributos": {
                            "Cor": [
                                ("Cinza Grafite", Decimal("0"), Decimal("0")),
                                ("Branco Lunar", Decimal("3000"), Decimal("0")),
                                ("Vermelho Granada", Decimal("3500"), Decimal("0")),
                            ],
                            "Versão": [
                                ("XRE Híbrido", Decimal("0"), Decimal("0")),
                                ("XRV Premium", Decimal("15000"), Decimal("0")),
                            ],
                        },
                    },
                    {
                        "nome": "BMW X1 2023",
                        "descricao": "SUV premium alemã, motor 2.0 turbo 204cv. Interior em couro, teto solar panorâmico.",
                        "preco": Decimal("289000.00"),
                        "atributos": {
                            "Cor": [
                                ("Alpine White", Decimal("0"), Decimal("0")),
                                ("Black Sapphire", Decimal("4500"), Decimal("0")),
                                ("Phytonic Blue", Decimal("5500"), Decimal("0")),
                            ],
                        },
                    },
                ],
            },
            {
                "nome": "Motos",
                "produtos": [
                    {
                        "nome": "Honda CB 500F 2024",
                        "descricao": "Naked esportiva, motor bicilíndrico 471cc, 47cv. ABS de série, painel digital.",
                        "preco": Decimal("34990.00"),
                        "atributos": {
                            "Cor": [
                                ("Preta", Decimal("0"), Decimal("0")),
                                ("Vermelha Racing", Decimal("800"), Decimal("0")),
                            ],
                        },
                    },
                    {
                        "nome": "Yamaha MT-07 2024",
                        "descricao": "Roadster bicilíndrica 689cc, 74.8cv. Suspensão invertida, freios ABS.",
                        "preco": Decimal("48990.00"),
                        "atributos": {
                            "Cor": [
                                ("Storm Fluo", Decimal("0"), Decimal("0")),
                                ("Tech Black", Decimal("0"), Decimal("0")),
                                ("Ice Fluo", Decimal("1200"), Decimal("0")),
                            ],
                        },
                    },
                ],
            },
            {
                "nome": "Imóveis",
                "produtos": [
                    {
                        "nome": "Apartamento Centro - 85m²",
                        "descricao": "Apartamento 2 quartos (1 suíte), sala ampla, cozinha americana. Vaga de garagem coberta.",
                        "preco": Decimal("450000.00"),
                        "atributos": {
                            "Andar": [
                                ("Baixo (1-5)", Decimal("0"), Decimal("0")),
                                ("Médio (6-10)", Decimal("0"), Decimal("5")),
                                ("Alto (11+)", Decimal("0"), Decimal("12")),
                            ],
                        },
                    },
                    {
                        "nome": "Casa Condomínio - 180m²",
                        "descricao": "Casa 3 suítes, sala 2 ambientes, área gourmet, piscina. Condomínio fechado 24h.",
                        "preco": Decimal("890000.00"),
                        "atributos": {
                            "Acabamento": [
                                ("Padrão", Decimal("0"), Decimal("0")),
                                ("Alto Padrão", Decimal("0"), Decimal("15")),
                                ("Luxo", Decimal("0"), Decimal("30")),
                            ],
                        },
                    },
                ],
            },
        ],
    },
    "autolitros": {
        "nome_display": "AutoLitros",
        "admin_title": "AutoLitros Admin",
        "admin_subtitle": "Gestão de Bebidas Premium",
        "primary_color": "#7c2d12",  # Marrom/vinho
        "secondary_color": "#57534e",
        "accent_color": "#d97706",  # Laranja/âmbar
        "welcome_message": "Bem-vindo ao painel de gestão da AutoLitros! Aqui você gerencia nossa coleção de bebidas premium.",
        "categorias": [
            {
                "nome": "Cervejas Artesanais",
                "produtos": [
                    {
                        "nome": "IPA Tropical 500ml",
                        "descricao": "India Pale Ale com notas de maracujá e manga. IBU 45, ABV 6.5%.",
                        "preco": Decimal("24.90"),
                        "atributos": {
                            "Pack": [
                                ("Unidade", Decimal("0"), Decimal("0")),
                                ("Pack 6 unidades", Decimal("0"), Decimal("-10")),
                                ("Caixa 12 unidades", Decimal("0"), Decimal("-15")),
                            ],
                        },
                    },
                    {
                        "nome": "Stout Coffee Edition 355ml",
                        "descricao": "Stout encorpada com café especial. Notas de chocolate e caramelo. ABV 7.2%.",
                        "preco": Decimal("28.90"),
                        "atributos": {
                            "Pack": [
                                ("Unidade", Decimal("0"), Decimal("0")),
                                ("Pack 4 unidades", Decimal("0"), Decimal("-8")),
                            ],
                        },
                    },
                    {
                        "nome": "Pilsen Premium 600ml",
                        "descricao": "Pilsen puro malte, levemente lupulada. Refrescante e equilibrada. ABV 4.7%.",
                        "preco": Decimal("15.90"),
                        "atributos": {
                            "Pack": [
                                ("Unidade", Decimal("0"), Decimal("0")),
                                ("Pack 6 unidades", Decimal("0"), Decimal("-12")),
                                ("Caixa 24 unidades", Decimal("0"), Decimal("-20")),
                            ],
                        },
                    },
                ],
            },
            {
                "nome": "Vinhos",
                "produtos": [
                    {
                        "nome": "Malbec Reserva 2021",
                        "descricao": "Vinho argentino, uvas de Mendoza. Notas de frutas vermelhas e carvalho. 14.5% ABV.",
                        "preco": Decimal("89.90"),
                        "atributos": {
                            "Tamanho": [
                                ("750ml", Decimal("0"), Decimal("0")),
                                ("Magnum 1.5L", Decimal("0"), Decimal("80")),
                            ],
                        },
                    },
                    {
                        "nome": "Chardonnay Premium 2022",
                        "descricao": "Vinho branco chileno, fermentado em barrica. Notas de baunilha e frutas tropicais.",
                        "preco": Decimal("75.90"),
                        "atributos": {
                            "Tamanho": [
                                ("750ml", Decimal("0"), Decimal("0")),
                            ],
                        },
                    },
                    {
                        "nome": "Espumante Brut Rosé",
                        "descricao": "Espumante brasileiro método charmat. Notas de morango e flores brancas.",
                        "preco": Decimal("59.90"),
                        "atributos": {
                            "Tamanho": [
                                ("750ml", Decimal("0"), Decimal("0")),
                                ("Baby 375ml", Decimal("-20"), Decimal("0")),
                            ],
                        },
                    },
                ],
            },
            {
                "nome": "Whisky",
                "produtos": [
                    {
                        "nome": "Single Malt 12 Anos",
                        "descricao": "Whisky escocês single malt, maturado em barris de carvalho. Notas de mel e baunilha.",
                        "preco": Decimal("289.90"),
                        "atributos": {
                            "Tamanho": [
                                ("750ml", Decimal("0"), Decimal("0")),
                                ("1L", Decimal("0"), Decimal("25")),
                            ],
                        },
                    },
                    {
                        "nome": "Bourbon Premium",
                        "descricao": "Bourbon americano, maturado 8 anos. Notas de caramelo, baunilha e especiarias.",
                        "preco": Decimal("199.90"),
                        "atributos": {
                            "Tamanho": [
                                ("750ml", Decimal("0"), Decimal("0")),
                                ("1L", Decimal("0"), Decimal("25")),
                            ],
                        },
                    },
                ],
            },
            {
                "nome": "Destilados",
                "produtos": [
                    {
                        "nome": "Gin London Dry",
                        "descricao": "Gin artesanal brasileiro, botânicos selecionados. Notas cítricas e de zimbro.",
                        "preco": Decimal("129.90"),
                        "atributos": {
                            "Tamanho": [
                                ("750ml", Decimal("0"), Decimal("0")),
                            ],
                        },
                    },
                    {
                        "nome": "Cachaça Envelhecida",
                        "descricao": "Cachaça premium envelhecida 3 anos em barril de carvalho. Notas amadeiradas.",
                        "preco": Decimal("89.90"),
                        "atributos": {
                            "Tamanho": [
                                ("700ml", Decimal("0"), Decimal("0")),
                            ],
                        },
                    },
                ],
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Popula produtos de teste para cada empresa"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            type=str,
            help="Slug da empresa para popular (ex: autoprime, autolitros)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove produtos existentes antes de popular",
        )

    def handle(self, *args, **options):
        empresa_slug = options.get("empresa")
        clear = options.get("clear", False)

        if empresa_slug:
            # Popular apenas uma empresa
            try:
                empresa = Empresa.objects.get(slug=empresa_slug)
            except Empresa.DoesNotExist:
                raise CommandError(f"Empresa com slug '{empresa_slug}' não encontrada.")

            if empresa_slug not in PRODUTOS_POR_EMPRESA:
                raise CommandError(
                    f"Dados de produtos não definidos para '{empresa_slug}'. "
                    f"Empresas disponíveis: {', '.join(PRODUTOS_POR_EMPRESA.keys())}"
                )

            self._seed_empresa(empresa, PRODUTOS_POR_EMPRESA[empresa_slug], clear)
        else:
            # Popular todas as empresas
            for slug, dados in PRODUTOS_POR_EMPRESA.items():
                try:
                    empresa = Empresa.objects.get(slug=slug)
                    self._seed_empresa(empresa, dados, clear)
                except Empresa.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Empresa '{slug}' não encontrada. Pulando...")
                    )

        self.stdout.write(self.style.SUCCESS("\nSeed de produtos concluído!"))

    @transaction.atomic
    def _seed_empresa(self, empresa, dados, clear):
        """Popula produtos para uma empresa específica."""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Populando empresa: {empresa.nome}")
        self.stdout.write(f"{'='*60}")

        # Atualizar customizações da empresa
        empresa.admin_title = dados.get("admin_title", "")
        empresa.admin_subtitle = dados.get("admin_subtitle", "")
        empresa.primary_color = dados.get("primary_color", "#0ea5e9")
        empresa.secondary_color = dados.get("secondary_color", "#64748b")
        empresa.accent_color = dados.get("accent_color", "#f59e0b")
        empresa.welcome_message = dados.get("welcome_message", "")
        empresa.save()
        self.stdout.write(f"  Customizações atualizadas")

        if clear:
            # Limpar produtos existentes
            count = Produto.objects.filter(empresa=empresa).count()
            Produto.objects.filter(empresa=empresa).delete()
            Categoria.objects.filter(empresa=empresa).delete()
            Atributo.objects.filter(empresa=empresa).delete()
            self.stdout.write(self.style.WARNING(f"  Removidos {count} produtos existentes"))

        # Criar/obter inventário padrão
        inventario, created = Inventario.objects.get_or_create(
            empresa=empresa,
            nome="Estoque Principal",
            defaults={
                "is_ativo": True,
                "exibir_na_vitrine": True,
            },
        )
        if created:
            self.stdout.write(f"  Inventário criado: {inventario.nome}")

        # Criar atributos globais para a empresa
        atributos_cache = {}

        for cat_dados in dados["categorias"]:
            # Criar categoria
            categoria, created = Categoria.objects.get_or_create(
                empresa=empresa,
                categoria=cat_dados["nome"],
            )
            status = "criada" if created else "existente"
            self.stdout.write(f"\n  Categoria: {categoria.categoria} ({status})")

            for prod_dados in cat_dados["produtos"]:
                # Criar produto
                produto, created = Produto.objects.get_or_create(
                    empresa=empresa,
                    produto=prod_dados["nome"],
                    defaults={
                        "descricao": prod_dados["descricao"],
                        "preco": prod_dados["preco"],
                        "categoria": categoria,
                        "disponivel": True,
                    },
                )

                if not created:
                    # Atualiza dados se já existe
                    produto.descricao = prod_dados["descricao"]
                    produto.preco = prod_dados["preco"]
                    produto.categoria = categoria
                    produto.save()

                status = "criado" if created else "atualizado"
                self.stdout.write(f"    Produto: {produto.produto} ({status})")

                # Criar atributos e variações
                self._criar_variacoes(
                    empresa, produto, prod_dados.get("atributos", {}), atributos_cache
                )

                # Criar saldo no inventário para cada variação
                for variacao in produto.variacoes.all():
                    saldo, _ = InventarioSaldo.objects.update_or_create(
                        inventario=inventario,
                        produto=produto,
                        defaults={"quantidade": 10},  # Estoque inicial
                    )
                    # Atualiza estoque da variação
                    variacao.estoque = 10
                    variacao.save(update_fields=["estoque"])

        self.stdout.write(self.style.SUCCESS(f"\n  Empresa {empresa.nome} populada com sucesso!"))

    def _criar_variacoes(self, empresa, produto, atributos_dict, atributos_cache):
        """Cria atributos, valores e variações para um produto."""
        import itertools

        valores_por_atributo = []

        for atributo_nome, valores in atributos_dict.items():
            # Criar/obter atributo
            cache_key = f"{empresa.pk}_{atributo_nome}"
            if cache_key not in atributos_cache:
                atributo, _ = Atributo.objects.get_or_create(
                    empresa=empresa,
                    nome=atributo_nome,
                )
                atributos_cache[cache_key] = atributo
            else:
                atributo = atributos_cache[cache_key]

            valores_lista = []
            for valor_nome, preco_adicional, percentual in valores:
                valor, _ = ValorAtributo.objects.get_or_create(
                    atributo=atributo,
                    valor=valor_nome,
                    defaults={
                        "preco_adicional": preco_adicional,
                        "percentual_adicional": percentual,
                    },
                )
                valores_lista.append(valor)

            valores_por_atributo.append(valores_lista)

        # Gerar todas as combinações de valores
        if valores_por_atributo:
            combinacoes = list(itertools.product(*valores_por_atributo))

            for combo in combinacoes:
                # Criar variação
                variacao, created = VariacaoProduto.objects.get_or_create(
                    produto=produto,
                    sku=self._gerar_sku_temp(produto, combo),
                    defaults={"estoque": 10},
                )

                if created:
                    variacao.valores.set(combo)
                    variacao.gerar_sku()  # Gera SKU correto
                    variacao.save()

    def _gerar_sku_temp(self, produto, valores):
        """Gera SKU temporário para busca."""
        valores_ids = "-".join(str(v.pk) for v in sorted(valores, key=lambda x: x.pk))
        return f"{produto.pk}-{valores_ids}"
