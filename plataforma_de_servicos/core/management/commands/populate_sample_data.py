"""
Management command para popular o banco de dados com dados de exemplo.
Inclui categorias, produtos (carros, motos, imóveis), atributos detalhados,
variações, inventários, e ordens de compra.
"""
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from plataforma_de_servicos.corretor.models import InteresseCompra
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
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.models.ordem_compra import ItemOrdemCompra
from plataforma_de_servicos.vendas.models.ordem_compra import OrdemCompra

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

        # Criar atributos detalhados
        atributos = self._criar_atributos()

        # Criar produtos com descrições
        produtos = self._criar_produtos(categorias, atributos)

        # Criar inventários
        inventarios = self._criar_inventarios()

        # Criar movimentações de estoque com quantidades maiores
        self._criar_movimentacoes_estoque(produtos, inventarios, admin)

        # Criar ordens de compra de exemplo
        self._criar_ordens_compra(produtos, empresa, admin)

        self.stdout.write(self.style.SUCCESS("Dados de exemplo criados com sucesso!"))
        self._mostrar_resumo()

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
        Funcionario.objects.all().delete()
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

        # Criar empresa para o vendedor
        empresa_vendedor, _ = Empresa.objects.get_or_create(
            nome="AutoPrime Veículos e Imóveis",
            defaults={
                "email": "contato@autoprime.com.br",
            },
        )

        # Criar funcionário como corretor
        Funcionario.objects.get_or_create(
            usuario=vendedor,
            defaults={
                "empresa": empresa_vendedor,
                "cargo": "Corretor",
                "is_corretor": True,
            },
        )

        return admin, vendedor

    def _criar_empresa(self):
        """Cria empresa de exemplo"""
        self.stdout.write("  Criando empresa...")

        empresa, _ = Empresa.objects.get_or_create(
            nome="AutoPrime Veículos e Imóveis",
            defaults={
                "email": "contato@autoprime.com.br",
            },
        )
        return empresa

    def _criar_categorias(self):
        """Cria categorias de exemplo"""
        self.stdout.write("  Criando categorias...")

        categorias = {}
        dados = [
            ("Carros Novos", "carros-novos"),
            ("Carros Seminovos", "carros-seminovos"),
            ("Motos", "motos"),
            ("Apartamentos", "apartamentos"),
            ("Casas", "casas"),
            ("Terrenos", "terrenos"),
            ("Comercial", "comercial"),
        ]

        for nome, slug in dados:
            cat, _ = Categoria.objects.get_or_create(
                categoria=nome,
                defaults={"slug": slug},
            )
            categorias[slug] = cat

        return categorias

    def _criar_atributos(self):
        """Cria atributos detalhados para veículos e imóveis"""
        self.stdout.write("  Criando atributos detalhados...")

        atributos = {}

        # ========== ATRIBUTOS GERAIS ==========

        # Cor
        cor, _ = Atributo.objects.get_or_create(nome="Cor")
        cores = [
            ("Preto", Decimal("0")),
            ("Branco", Decimal("0")),
            ("Prata", Decimal("0")),
            ("Cinza Grafite", Decimal("0")),
            ("Vermelho", Decimal("1500")),
            ("Azul", Decimal("1500")),
            ("Verde", Decimal("1500")),
            ("Dourado", Decimal("2500")),
            ("Marrom", Decimal("0")),
        ]
        for c, preco in cores:
            ValorAtributo.objects.get_or_create(
                atributo=cor, valor=c,
                defaults={"preco_adicional": preco},
            )
        atributos["cor"] = cor

        # Ano/Modelo
        ano, _ = Atributo.objects.get_or_create(nome="Ano/Modelo")
        anos = ["2021/2021", "2022/2022", "2023/2023", "2024/2024", "2024/2025", "2025/2025"]
        for a in anos:
            ValorAtributo.objects.get_or_create(atributo=ano, valor=a)
        atributos["ano"] = ano

        # ========== ATRIBUTOS DE CARROS ==========

        # Câmbio
        cambio, _ = Atributo.objects.get_or_create(nome="Câmbio")
        cambios = [
            ("Manual 5 marchas", Decimal("0")),
            ("Manual 6 marchas", Decimal("0")),
            ("Automático 6 marchas", Decimal("8000")),
            ("Automático CVT", Decimal("6000")),
            ("Automático 8 marchas", Decimal("12000")),
            ("Automatizado", Decimal("4000")),
        ]
        for c, preco in cambios:
            ValorAtributo.objects.get_or_create(
                atributo=cambio, valor=c,
                defaults={"preco_adicional": preco},
            )
        atributos["cambio"] = cambio

        # Combustível
        combustivel, _ = Atributo.objects.get_or_create(nome="Combustível")
        combustiveis = [
            ("Flex (Gasolina/Etanol)", Decimal("0")),
            ("Gasolina", Decimal("0")),
            ("Diesel", Decimal("15000")),
            ("Híbrido", Decimal("35000")),
            ("Elétrico", Decimal("50000")),
        ]
        for c, preco in combustiveis:
            ValorAtributo.objects.get_or_create(
                atributo=combustivel, valor=c,
                defaults={"preco_adicional": preco},
            )
        atributos["combustivel"] = combustivel

        # Motor
        motor, _ = Atributo.objects.get_or_create(nome="Motor")
        motores = [
            ("1.0 Aspirado", Decimal("0")),
            ("1.0 Turbo", Decimal("8000")),
            ("1.3 Aspirado", Decimal("3000")),
            ("1.5 Aspirado", Decimal("5000")),
            ("1.6 Aspirado", Decimal("7000")),
            ("2.0 Aspirado", Decimal("12000")),
            ("2.0 Turbo", Decimal("25000")),
            ("2.0 Diesel", Decimal("20000")),
        ]
        for m, preco in motores:
            ValorAtributo.objects.get_or_create(
                atributo=motor, valor=m,
                defaults={"preco_adicional": preco},
            )
        atributos["motor"] = motor

        # Portas
        portas, _ = Atributo.objects.get_or_create(nome="Portas")
        for p in ["2 Portas", "4 Portas", "5 Portas (Hatch)"]:
            ValorAtributo.objects.get_or_create(atributo=portas, valor=p)
        atributos["portas"] = portas

        # Direção
        direcao, _ = Atributo.objects.get_or_create(nome="Direção")
        direcoes = [
            ("Mecânica", Decimal("0")),
            ("Hidráulica", Decimal("2000")),
            ("Elétrica", Decimal("3500")),
        ]
        for d, preco in direcoes:
            ValorAtributo.objects.get_or_create(
                atributo=direcao, valor=d,
                defaults={"preco_adicional": preco},
            )
        atributos["direcao"] = direcao

        # Ar Condicionado
        ar, _ = Atributo.objects.get_or_create(nome="Ar Condicionado")
        ares = [
            ("Sem Ar", Decimal("0")),
            ("Ar Condicionado", Decimal("4000")),
            ("Ar Digital (Dual Zone)", Decimal("6000")),
        ]
        for a, preco in ares:
            ValorAtributo.objects.get_or_create(
                atributo=ar, valor=a,
                defaults={"preco_adicional": preco},
            )
        atributos["ar"] = ar

        # Pacote de Segurança
        seguranca, _ = Atributo.objects.get_or_create(nome="Pacote Segurança")
        segurancas = [
            ("Básico (2 Airbags + ABS)", Decimal("0")),
            ("Intermediário (4 Airbags + ESP)", Decimal("5000")),
            ("Completo (6 Airbags + ESP + Sensores)", Decimal("12000")),
            ("Premium (8 Airbags + Assistências)", Decimal("20000")),
        ]
        for s, preco in segurancas:
            ValorAtributo.objects.get_or_create(
                atributo=seguranca, valor=s,
                defaults={"preco_adicional": preco},
            )
        atributos["seguranca"] = seguranca

        # ========== ATRIBUTOS DE MOTOS ==========

        # Cilindrada
        cilindrada, _ = Atributo.objects.get_or_create(nome="Cilindrada")
        cilindradas = ["125cc", "150cc", "160cc", "250cc", "300cc", "500cc", "650cc", "900cc", "1000cc"]
        for c in cilindradas:
            ValorAtributo.objects.get_or_create(atributo=cilindrada, valor=c)
        atributos["cilindrada"] = cilindrada

        # Tipo de Moto
        tipo_moto, _ = Atributo.objects.get_or_create(nome="Estilo")
        estilos = ["Street", "Naked", "Sport", "Custom", "Trail", "Scooter", "Adventure", "Touring"]
        for t in estilos:
            ValorAtributo.objects.get_or_create(atributo=tipo_moto, valor=t)
        atributos["tipo_moto"] = tipo_moto

        # Freio
        freio_moto, _ = Atributo.objects.get_or_create(nome="Sistema de Freio")
        freios = [
            ("Tambor/Disco", Decimal("0")),
            ("Disco/Disco", Decimal("800")),
            ("CBS (Combined Brake)", Decimal("1200")),
            ("ABS", Decimal("2500")),
        ]
        for f, preco in freios:
            ValorAtributo.objects.get_or_create(
                atributo=freio_moto, valor=f,
                defaults={"preco_adicional": preco},
            )
        atributos["freio_moto"] = freio_moto

        # Partida
        partida, _ = Atributo.objects.get_or_create(nome="Partida")
        partidas = [
            ("Pedal", Decimal("0")),
            ("Elétrica", Decimal("500")),
            ("Elétrica + Pedal", Decimal("300")),
        ]
        for p, preco in partidas:
            ValorAtributo.objects.get_or_create(
                atributo=partida, valor=p,
                defaults={"preco_adicional": preco},
            )
        atributos["partida"] = partida

        # ========== ATRIBUTOS DE IMÓVEIS ==========

        # Quartos
        quartos, _ = Atributo.objects.get_or_create(nome="Quartos")
        for q in ["1 Quarto", "2 Quartos", "3 Quartos", "4 Quartos", "5+ Quartos"]:
            ValorAtributo.objects.get_or_create(atributo=quartos, valor=q)
        atributos["quartos"] = quartos

        # Suítes
        suites, _ = Atributo.objects.get_or_create(nome="Suítes")
        for s in ["Sem Suíte", "1 Suíte", "2 Suítes", "3 Suítes", "4+ Suítes"]:
            ValorAtributo.objects.get_or_create(atributo=suites, valor=s)
        atributos["suites"] = suites

        # Vagas de Garagem
        vagas, _ = Atributo.objects.get_or_create(nome="Vagas")
        vagas_opcoes = [
            ("Sem Vaga", Decimal("0")),
            ("1 Vaga", Decimal("30000")),
            ("2 Vagas", Decimal("60000")),
            ("3 Vagas", Decimal("90000")),
            ("4+ Vagas", Decimal("120000")),
        ]
        for v, preco in vagas_opcoes:
            ValorAtributo.objects.get_or_create(
                atributo=vagas, valor=v,
                defaults={"preco_adicional": preco},
            )
        atributos["vagas"] = vagas

        # Área
        area, _ = Atributo.objects.get_or_create(nome="Área")
        areas = ["40-60m²", "60-80m²", "80-100m²", "100-150m²", "150-200m²", "200-300m²", "300m²+"]
        for a in areas:
            ValorAtributo.objects.get_or_create(atributo=area, valor=a)
        atributos["area"] = area

        # Condomínio
        condominio, _ = Atributo.objects.get_or_create(nome="Condomínio")
        condominios = [
            ("Sem Condomínio", Decimal("0")),
            ("Condomínio Básico", Decimal("0")),
            ("Condomínio com Lazer", Decimal("0")),
            ("Condomínio Clube", Decimal("0")),
            ("Alto Padrão", Decimal("0")),
        ]
        for c, preco in condominios:
            ValorAtributo.objects.get_or_create(
                atributo=condominio, valor=c,
                defaults={"preco_adicional": preco},
            )
        atributos["condominio"] = condominio

        # Posição Solar
        sol, _ = Atributo.objects.get_or_create(nome="Posição Solar")
        for s in ["Nascente", "Poente", "Norte", "Sul"]:
            ValorAtributo.objects.get_or_create(atributo=sol, valor=s)
        atributos["sol"] = sol

        # Andar
        andar, _ = Atributo.objects.get_or_create(nome="Andar")
        for a in ["Térreo", "Baixo (1-5)", "Médio (6-15)", "Alto (16+)", "Cobertura"]:
            ValorAtributo.objects.get_or_create(atributo=andar, valor=a)
        atributos["andar"] = andar

        # Mobiliado
        mobiliado, _ = Atributo.objects.get_or_create(nome="Mobiliado")
        mobiliado_opcoes = [
            ("Não Mobiliado", Decimal("0")),
            ("Semi-Mobiliado (Planejados)", Decimal("25000")),
            ("Mobiliado (Completo)", Decimal("50000")),
        ]
        for m, preco in mobiliado_opcoes:
            ValorAtributo.objects.get_or_create(
                atributo=mobiliado, valor=m,
                defaults={"preco_adicional": preco},
            )
        atributos["mobiliado"] = mobiliado

        # Lazer
        lazer, _ = Atributo.objects.get_or_create(nome="Itens de Lazer")
        lazer_opcoes = [
            "Piscina", "Academia", "Salão de Festas", "Churrasqueira",
            "Playground", "Quadra", "Sauna", "Espaço Gourmet", "Coworking",
        ]
        for l in lazer_opcoes:
            ValorAtributo.objects.get_or_create(atributo=lazer, valor=l)
        atributos["lazer"] = lazer

        # Características Adicionais
        caracteristicas, _ = Atributo.objects.get_or_create(nome="Características")
        caracteristicas_opcoes = [
            "Varanda Gourmet", "Closet", "Lavabo", "Cozinha Americana",
            "Área de Serviço", "Depósito Privativo", "Pé-direito Duplo",
        ]
        for c in caracteristicas_opcoes:
            ValorAtributo.objects.get_or_create(atributo=caracteristicas, valor=c)
        atributos["caracteristicas"] = caracteristicas

        # Acabamento
        acabamento, _ = Atributo.objects.get_or_create(nome="Acabamento")
        acabamento_opcoes = ["Piso Frio", "Porcelanato", "Laminado", "Vinílico", "Madeira"]
        for a in acabamento_opcoes:
            ValorAtributo.objects.get_or_create(atributo=acabamento, valor=a)
        atributos["acabamento"] = acabamento

        return atributos

    def _criar_produtos(self, categorias, atributos):
        """Cria produtos com descrições detalhadas"""
        self.stdout.write("  Criando produtos com descrições...")

        produtos = []

        # === CARROS NOVOS ===
        carros_novos = [
            {
                "nome": "Toyota Corolla Cross XRE",
                "preco": Decimal("189990.00"),
                "descricao": "O Toyota Corolla Cross XRE combina o DNA do sedan mais vendido do Brasil com a versatilidade de um SUV. Motor 2.0 Flex com 177cv, câmbio CVT com modo Sport, tração dianteira, central multimídia de 9 polegadas com Android Auto e Apple CarPlay, ar condicionado digital dual zone, bancos em couro sintético, sensores de estacionamento e câmera de ré. Garantia de 5 anos.",
            },
            {
                "nome": "Honda Civic Touring",
                "preco": Decimal("219900.00"),
                "descricao": "O Honda Civic Touring é a versão mais completa do icônico sedan japonês. Motor 1.5 Turbo com 173cv, câmbio CVT com borboletas no volante, painel digital de 10.2 polegadas, Honda Sensing (assistente de condução), bancos em couro, teto solar elétrico, carregador wireless, faróis full LED e acabamento premium. Referência em qualidade e durabilidade.",
            },
            {
                "nome": "Volkswagen T-Cross Highline",
                "preco": Decimal("159990.00"),
                "descricao": "O VW T-Cross Highline oferece o melhor da engenharia alemã em um SUV compacto. Motor 1.4 TSI com 150cv, câmbio automático de 6 marchas Tiptronic, painel digital Active Info Display, central multimídia VW Play com tela de 10 polegadas, teto solar panorâmico, sensores de estacionamento dianteiro e traseiro, 6 airbags e controle de estabilidade ESC.",
            },
            {
                "nome": "Chevrolet Tracker Premier",
                "preco": Decimal("169900.00"),
                "descricao": "O Chevrolet Tracker Premier é o SUV compacto mais conectado do Brasil. Motor 1.2 Turbo Ecotec com 133cv, câmbio automático de 6 velocidades, OnStar com 4G Wi-Fi integrado, MyLink com tela de 8 polegadas, alerta de colisão frontal, frenagem autônoma de emergência, detector de fadiga e mais de 12 sistemas de assistência ao motorista.",
            },
            {
                "nome": "Hyundai Creta Ultimate",
                "preco": Decimal("184990.00"),
                "descricao": "O Hyundai Creta Ultimate entrega luxo e tecnologia em um SUV compacto. Motor 2.0 Flex com 167cv, câmbio automático de 6 marchas, painel digital de 10.25 polegadas, ar condicionado digital, bancos em couro com ventilação, teto solar panorâmico, som Bose com 8 alto-falantes, carregador wireless e sistema BlueLink de conectividade.",
            },
            {
                "nome": "Jeep Compass Limited",
                "preco": Decimal("199990.00"),
                "descricao": "O Jeep Compass Limited é sinônimo de aventura com conforto. Motor 1.3 Turbo Flex T270 com 185cv, câmbio automático de 6 marchas, tração 4x2, interior com bancos em couro, central Uconnect de 10.1 polegadas, carregador por indução, câmera 360 graus, sensor de ponto cego e a lendária capacidade off-road da marca.",
            },
            {
                "nome": "Fiat Pulse Impetus",
                "preco": Decimal("129990.00"),
                "descricao": "O Fiat Pulse Impetus é o primeiro SUV da Fiat produzido no Brasil. Motor 1.0 Turbo T200 com 130cv, câmbio CVT com modo Sport, central multimídia de 10.1 polegadas com wireless Android Auto e CarPlay, painel digital de 7 polegadas, ar condicionado digital, chave presencial, partida por botão e design italiano exclusivo.",
            },
            {
                "nome": "Nissan Kicks Exclusive",
                "preco": Decimal("149990.00"),
                "descricao": "O Nissan Kicks Exclusive oferece espaço e tecnologia. Motor 1.6 Flex com 114cv (E-Power disponível), câmbio CVT Xtronic, interior espaçoso com porta-malas de 432 litros, central multimídia de 8 polegadas, ar condicionado digital, câmera 360 graus, Around View Monitor e sistema de som Bose Personal.",
            },
        ]

        for dados in carros_novos:
            produto, _ = Produto.objects.get_or_create(
                produto=dados["nome"],
                defaults={
                    "preco": dados["preco"],
                    "estoque": 0,
                    "categoria": categorias["carros-novos"],
                    "descricao": dados["descricao"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_carro(produto, atributos)

        # === CARROS SEMINOVOS ===
        carros_usados = [
            {
                "nome": "Honda Fit EXL 2022",
                "preco": Decimal("89990.00"),
                "descricao": "Honda Fit EXL 2022 com apenas 28.000 km rodados. Motor 1.5 i-VTEC com 116cv, câmbio CVT, único dono, todas as revisões na concessionária, IPVA 2024 pago, licenciamento em dia. Interior impecável, bancos em couro, ar digital, câmera de ré, sensor de estacionamento. Garantia de procedência.",
            },
            {
                "nome": "Volkswagen Polo TSI 2023",
                "preco": Decimal("94990.00"),
                "descricao": "VW Polo Highline TSI 2023, 15.000 km, único dono. Motor 1.0 TSI com 128cv, câmbio automático de 6 marchas, Active Info Display, VW Play, teto solar, sensor de estacionamento. Veículo de garagem, sem detalhes, pronto para transferência.",
            },
            {
                "nome": "Renault Kwid Zen 2021",
                "preco": Decimal("49990.00"),
                "descricao": "Renault Kwid Zen 2021, econômico e compacto. Motor 1.0 SCe com 66cv, câmbio manual de 5 marchas, ar condicionado, direção elétrica, vidros elétricos, travas elétricas, alarme. 42.000 km rodados, ótimo custo-benefício para cidade.",
            },
        ]

        for dados in carros_usados:
            produto, _ = Produto.objects.get_or_create(
                produto=dados["nome"],
                defaults={
                    "preco": dados["preco"],
                    "estoque": 0,
                    "categoria": categorias["carros-seminovos"],
                    "descricao": dados["descricao"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_carro_usado(produto, atributos)

        # === MOTOS ===
        motos = [
            {
                "nome": "Honda CB 500F",
                "preco": Decimal("36990.00"),
                "descricao": "A Honda CB 500F é a naked ideal para o dia a dia e viagens. Motor bicilíndrico de 471cc com 50,4cv, injeção eletrônica PGM-FI, câmbio de 6 marchas, freio ABS de dois canais, painel LCD completo, farol full LED e design agressivo. Consumo médio de 22 km/l, baixo custo de manutenção.",
            },
            {
                "nome": "Yamaha MT-03",
                "preco": Decimal("32990.00"),
                "descricao": "A Yamaha MT-03 é uma naked esportiva com DNA de pista. Motor bicilíndrico de 321cc com 42cv, câmbio de 6 marchas, freio ABS, painel digital invertido, farol LED com design agressivo e escapamento esportivo. Peso de apenas 168kg, ideal para iniciantes e experientes.",
            },
            {
                "nome": "Kawasaki Ninja 400",
                "preco": Decimal("34990.00"),
                "descricao": "A Kawasaki Ninja 400 é referência entre as esportivas de entrada. Motor bicilíndrico de 399cc com 49cv, câmbio assist & slipper, ABS de duplo canal, painel digital, faróis LED e carenagem aerodinâmica. Ergonomia equilibrada para uso diário e pista.",
            },
            {
                "nome": "BMW G 310 R",
                "preco": Decimal("31990.00"),
                "descricao": "A BMW G 310 R traz a qualidade alemã para as motos de entrada. Motor monocilíndrico de 313cc com 34cv, câmbio de 6 marchas, ABS de série, painel LCD completo, farol LED e design roadster. Baixo custo de manutenção com a qualidade BMW.",
            },
            {
                "nome": "Honda CG 160 Titan",
                "preco": Decimal("16490.00"),
                "descricao": "A Honda CG 160 Titan é a moto mais popular do Brasil. Motor OHC de 162,7cc com 15cv, injeção eletrônica, partida elétrica, painel digital, freio CBS (Combined Brake System), consumo de até 45 km/l. Ideal para trabalho e economia.",
            },
            {
                "nome": "Yamaha Fazer 250",
                "preco": Decimal("21490.00"),
                "descricao": "A Yamaha Fazer 250 é versátil para cidade e estrada. Motor monocilíndrico de 249cc com 21cv, injeção eletrônica, freio a disco dianteiro e traseiro com ABS, painel digital, farol LED e carenagem semi-integral. Conforto e economia.",
            },
            {
                "nome": "Honda PCX 160",
                "preco": Decimal("17990.00"),
                "descricao": "O Honda PCX 160 é o scooter premium mais vendido. Motor eSP+ de 156,9cc com 16cv, câmbio automático CVT, partida com Smart Key, painel digital com conectividade Honda RoadSync, porta USB, bagageiro de 30 litros e consumo de 40 km/l.",
            },
            {
                "nome": "Triumph Tiger 900 Rally Pro",
                "preco": Decimal("89900.00"),
                "descricao": "A Triumph Tiger 900 Rally Pro é uma adventure de alta performance. Motor tricilíndrico de 888cc com 95cv, câmbio de 6 marchas com quickshifter, 6 modos de pilotagem, controle de tração, ABS em curva, suspensão Showa ajustável, painel TFT colorido e preparação para viagens longas.",
            },
        ]

        for dados in motos:
            produto, _ = Produto.objects.get_or_create(
                produto=dados["nome"],
                defaults={
                    "preco": dados["preco"],
                    "estoque": 0,
                    "categoria": categorias["motos"],
                    "descricao": dados["descricao"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_moto(produto, atributos)

        # === APARTAMENTOS ===
        apartamentos = [
            {
                "nome": "Apartamento Alto Padrão - Jardins",
                "preco": Decimal("1850000.00"),
                "descricao": "Apartamento de alto padrão no bairro Jardins. 180m² de área privativa, 3 suítes com closet, living amplo com varanda gourmet, cozinha planejada Ornare, 3 vagas de garagem, depósito privativo. Condomínio clube com academia, piscina aquecida, spa, salão de festas e segurança 24h. Andar alto com vista panorâmica.",
            },
            {
                "nome": "Studio Moderno - Pinheiros",
                "preco": Decimal("485000.00"),
                "descricao": "Studio moderno e funcional em Pinheiros. 38m² otimizados com conceito aberto, varanda, cozinha americana equipada, banheiro com ventilação natural. Condomínio com coworking, rooftop, bike sharing, lavanderia compartilhada e pet place. A 300m do metrô, ideal para jovens profissionais.",
            },
            {
                "nome": "Apartamento Familiar - Moema",
                "preco": Decimal("1250000.00"),
                "descricao": "Apartamento espaçoso para família em Moema. 120m², 3 quartos sendo 1 suíte, sala para 2 ambientes, varanda com churrasqueira, cozinha planejada, área de serviço, 2 vagas cobertas. Condomínio com playground, salão de jogos, piscina e quadra. Próximo a escolas e parque Ibirapuera.",
            },
            {
                "nome": "Cobertura Duplex - Itaim Bibi",
                "preco": Decimal("3500000.00"),
                "descricao": "Cobertura duplex exclusiva no Itaim Bibi. 280m² + 100m² de terraço privativo com piscina e spa. 4 suítes, living triplo, home office, cozinha gourmet, adega climatizada, 4 vagas. Acabamento de luxo com automação residencial completa. Vista 360° para a cidade.",
            },
            {
                "nome": "Apartamento Compacto - Consolação",
                "preco": Decimal("395000.00"),
                "descricao": "Apartamento compacto e bem localizado na Consolação. 45m², 1 dormitório, sala integrada com cozinha americana, banheiro com box, 1 vaga. Prédio com lazer básico, portaria 24h. A 5 minutos do metrô e da Av. Paulista. Ótima opção para investimento ou moradia.",
            },
        ]

        for dados in apartamentos:
            produto, _ = Produto.objects.get_or_create(
                produto=dados["nome"],
                defaults={
                    "preco": dados["preco"],
                    "estoque": 0,
                    "categoria": categorias["apartamentos"],
                    "descricao": dados["descricao"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_apartamento(produto, atributos)

        # === CASAS ===
        casas = [
            {
                "nome": "Casa em Condomínio - Alphaville",
                "preco": Decimal("2800000.00"),
                "descricao": "Casa moderna em condomínio fechado de Alphaville. 350m² de construção em terreno de 500m². 4 suítes com closet, living integrado com pé direito duplo, cozinha gourmet, área de lazer com piscina, churrasqueira e forno de pizza. Acabamento de alto padrão, automação, energia solar. Condomínio com segurança 24h, área verde e clube completo.",
            },
            {
                "nome": "Casa Térrea - Cidade Jardim",
                "preco": Decimal("4500000.00"),
                "descricao": "Residência térrea no nobre bairro Cidade Jardim. 400m² em terreno de 800m². 5 suítes, sala para 4 ambientes, escritório, cozinha com ilha, dependência completa. Jardim paisagístico, piscina com raia de 15m, espaço gourmet coberto. Projeto arquitetônico exclusivo, materiais importados.",
            },
            {
                "nome": "Sobrado Novo - Brooklin",
                "preco": Decimal("1950000.00"),
                "descricao": "Sobrado novo no Brooklin. 280m² em 3 pavimentos. 4 quartos sendo 2 suítes, living amplo, cozinha americana, lavabo, quintal com churrasqueira, 3 vagas. Acabamento contemporâneo, piso em porcelanato, esquadrias em alumínio. Rua tranquila, próximo a comércios e transporte.",
            },
        ]

        for dados in casas:
            produto, _ = Produto.objects.get_or_create(
                produto=dados["nome"],
                defaults={
                    "preco": dados["preco"],
                    "estoque": 0,
                    "categoria": categorias["casas"],
                    "descricao": dados["descricao"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_casa(produto, atributos)

        # === TERRENOS ===
        terrenos = [
            {
                "nome": "Terreno em Condomínio - Granja Viana",
                "preco": Decimal("450000.00"),
                "descricao": "Terreno plano em condomínio fechado na Granja Viana. 600m² com frente de 20m, pronto para construir. Condomínio com segurança 24h, área de lazer com quadras, trilhas e nascente. Documentação em dia, aceita financiamento. Projeto arquitetônico incluso.",
            },
            {
                "nome": "Lote Comercial - Marginal Pinheiros",
                "preco": Decimal("2500000.00"),
                "descricao": "Lote comercial em localização privilegiada na Marginal Pinheiros. 1.200m² com frente para avenida, zoneamento misto (ZM), alta visibilidade. Ideal para empreendimento comercial, hotel ou residencial. Documentação completa, sem restrições.",
            },
        ]

        for dados in terrenos:
            produto, _ = Produto.objects.get_or_create(
                produto=dados["nome"],
                defaults={
                    "preco": dados["preco"],
                    "estoque": 0,
                    "categoria": categorias["terrenos"],
                    "descricao": dados["descricao"],
                },
            )
            produtos.append(produto)
            # Terrenos não têm variações

        # === COMERCIAL ===
        comerciais = [
            {
                "nome": "Sala Comercial - Faria Lima",
                "preco": Decimal("850000.00"),
                "descricao": "Sala comercial na Av. Faria Lima, coração financeiro de SP. 80m² em andar alto de edifício triple A. Piso elevado, ar condicionado central, 2 vagas. Prédio com certificação LEED, heliponto, restaurante, auditório. Ideal para empresas de tecnologia, advocacia ou consultoria.",
            },
            {
                "nome": "Loja de Rua - Oscar Freire",
                "preco": Decimal("3200000.00"),
                "descricao": "Loja de rua na prestigiada Oscar Freire. 150m² em 2 pavimentos, vitrine de 8m, mezanino, 2 banheiros, copa. Alto fluxo de pedestres, vizinhança de marcas internacionais. Contrato de locação disponível para investidores. Excelente rentabilidade.",
            },
            {
                "nome": "Galpão Logístico - Guarulhos",
                "preco": Decimal("4800000.00"),
                "descricao": "Galpão logístico em condomínio em Guarulhos. 2.000m² de área construída, pé direito de 12m, piso com capacidade de 5 ton/m², 6 docas, pátio de manobra. Sprinklers, portaria blindada, gerador. Próximo ao Aeroporto e Rodoanel, ideal para e-commerce e distribuição.",
            },
        ]

        for dados in comerciais:
            produto, _ = Produto.objects.get_or_create(
                produto=dados["nome"],
                defaults={
                    "preco": dados["preco"],
                    "estoque": 0,
                    "categoria": categorias["comercial"],
                    "descricao": dados["descricao"],
                },
            )
            produtos.append(produto)
            self._criar_variacoes_comercial(produto, atributos)

        return produtos

    def _criar_variacoes_carro(self, produto, atributos):
        """Cria variações para carros novos"""
        cores = list(ValorAtributo.objects.filter(atributo=atributos["cor"]))[:4]
        anos = list(ValorAtributo.objects.filter(atributo=atributos["ano"]).order_by("-valor"))[:2]
        cambios = list(ValorAtributo.objects.filter(atributo=atributos["cambio"]))[:3]

        count = 0
        for cor in cores:
            for ano in anos:
                for cambio in cambios:
                    if count >= 8:  # Limitar variações
                        return
                    variacao = VariacaoProduto.objects.create(
                        produto=produto,
                        preco=produto.preco,
                        estoque=0,
                    )
                    variacao.valores.add(cor, ano, cambio)
                    variacao.gerar_sku()
                    variacao.save()
                    count += 1

    def _criar_variacoes_carro_usado(self, produto, atributos):
        """Cria variações para carros usados (menos opções)"""
        cores = list(ValorAtributo.objects.filter(atributo=atributos["cor"]))[:2]

        for cor in cores:
            variacao = VariacaoProduto.objects.create(
                produto=produto,
                preco=produto.preco,
                estoque=0,
            )
            variacao.valores.add(cor)
            variacao.gerar_sku()
            variacao.save()

    def _criar_variacoes_moto(self, produto, atributos):
        """Cria variações para motos"""
        cores = list(ValorAtributo.objects.filter(atributo=atributos["cor"]))[:4]
        anos = list(ValorAtributo.objects.filter(atributo=atributos["ano"]).order_by("-valor"))[:2]
        freios = list(ValorAtributo.objects.filter(atributo=atributos["freio_moto"]))[:2]

        count = 0
        for cor in cores:
            for ano in anos:
                for freio in freios:
                    if count >= 6:
                        return
                    variacao = VariacaoProduto.objects.create(
                        produto=produto,
                        preco=produto.preco,
                        estoque=0,
                    )
                    variacao.valores.add(cor, ano, freio)
                    variacao.gerar_sku()
                    variacao.save()
                    count += 1

    def _criar_variacoes_apartamento(self, produto, atributos):
        """Cria variações para apartamentos"""
        andares = list(ValorAtributo.objects.filter(atributo=atributos["andar"]))[:3]
        posicoes = list(ValorAtributo.objects.filter(atributo=atributos["sol"]))[:2]
        mobiliado_opts = list(ValorAtributo.objects.filter(atributo=atributos["mobiliado"]))[:2]

        for andar in andares:
            for sol in posicoes:
                for mobiliado in mobiliado_opts:
                    variacao = VariacaoProduto.objects.create(
                        produto=produto,
                        preco=produto.preco,
                        estoque=0,
                    )
                    variacao.valores.add(andar, sol, mobiliado)
                    variacao.gerar_sku()
                    variacao.save()

    def _criar_variacoes_casa(self, produto, atributos):
        """Cria variações para casas (quartos e vagas)"""
        quartos_valores = list(ValorAtributo.objects.filter(atributo=atributos["quartos"]))[1:4]
        vagas_valores = list(ValorAtributo.objects.filter(atributo=atributos["vagas"]))[2:4]

        for quartos in quartos_valores:
            for vagas in vagas_valores:
                variacao = VariacaoProduto.objects.create(
                    produto=produto,
                    preco=produto.preco,
                    estoque=0,
                )
                variacao.valores.add(quartos, vagas)
                variacao.gerar_sku()
                variacao.save()

    def _criar_variacoes_comercial(self, produto, atributos):
        """Cria variações para imóveis comerciais"""
        areas = list(ValorAtributo.objects.filter(atributo=atributos["area"]))[2:5]

        for area in areas:
            variacao = VariacaoProduto.objects.create(
                produto=produto,
                preco=produto.preco,
                estoque=0,
            )
            variacao.valores.add(area)
            variacao.gerar_sku()
            variacao.save()

    def _criar_inventarios(self):
        """Cria inventários de exemplo"""
        self.stdout.write("  Criando inventários...")

        inventarios = {}

        dados = [
            ("Loja São Paulo - Faria Lima", True),
            ("Loja Rio de Janeiro - Barra", True),
            ("Loja Belo Horizonte - Savassi", True),
            ("Showroom Premium SP", True),
            ("Pátio de Veículos", False),
        ]

        for nome, exibir in dados:
            inv, _ = Inventario.objects.get_or_create(
                nome=nome,
                defaults={"exibir_na_vitrine": exibir},
            )
            inventarios[nome] = inv

        return inventarios

    def _criar_movimentacoes_estoque(self, produtos, inventarios, funcionario):
        """Cria entradas de estoque com quantidades adequadas."""
        self.stdout.write("  Criando movimentações de estoque...")

        inv_sp = inventarios["Loja São Paulo - Faria Lima"]
        inv_rj = inventarios["Loja Rio de Janeiro - Barra"]
        inv_bh = inventarios["Loja Belo Horizonte - Savassi"]
        inv_patio = inventarios["Pátio de Veículos"]

        # Distribuir produtos entre lojas
        for i, produto in enumerate(produtos):
            # Determinar inventário principal
            if i % 4 == 0:
                inv_principal = inv_sp
            elif i % 4 == 1:
                inv_principal = inv_rj
            elif i % 4 == 2:
                inv_principal = inv_bh
            else:
                inv_principal = inv_patio

            # Criar entrada
            self._criar_entrada_completa(produto, inv_principal, funcionario)

        self.stdout.write(f"    Total de produtos com estoque: {Produto.objects.filter(estoque__gt=0).count()}")

    def _criar_entrada_completa(self, produto, inventario, funcionario):
        """Cria entrada de estoque para todas as variações de um produto."""
        entrada = Estoque.objects.create(
            funcionario=funcionario,
            movimento=Movimento.ENTRADA.value,
            inventario_destino=inventario,
            observacao=f"Entrada inicial - {produto.produto}",
        )

        variacoes = list(produto.variacoes.all())
        if variacoes:
            # Dar estoque para 60% das variações
            num_variacoes = max(1, int(len(variacoes) * 0.6))
            variacoes_selecionadas = random.sample(variacoes, num_variacoes)

            for var in variacoes_selecionadas:
                # Veículos geralmente têm poucas unidades (1-3)
                # Imóveis são únicos (1)
                if "Apartamento" in produto.produto or "Casa" in produto.produto or "Terreno" in produto.produto or "Sala" in produto.produto or "Loja" in produto.produto or "Galpão" in produto.produto:
                    qtde = 1
                else:
                    qtde = random.randint(1, 3)

                EstoqueItens.objects.create(
                    estoque=entrada,
                    produto=produto,
                    variacao=var,
                    quantidade=qtde,
                    inventario=inventario,
                )
        else:
            # Produto sem variação
            if "Terreno" in produto.produto:
                qtde = 1
            else:
                qtde = random.randint(1, 3)

            EstoqueItens.objects.create(
                estoque=entrada,
                produto=produto,
                quantidade=qtde,
                inventario=inventario,
            )

        entrada.processar()

    def _criar_ordens_compra(self, produtos, empresa, usuario):
        """Cria ordens de compra de exemplo"""
        self.stdout.write("  Criando ordens de compra...")

        clientes = [
            ("Carlos Silva", "carlos@email.com", "11999998888"),
            ("Maria Santos", "maria@email.com", "21988887777"),
            ("Pedro Oliveira", "pedro@email.com", "31977776666"),
            ("Ana Costa", "ana@email.com", "11966665555"),
            ("Roberto Lima", "roberto@email.com", "21955554444"),
        ]

        produtos_com_estoque = [p for p in produtos if p.estoque > 0 or p.variacoes.filter(estoque__gt=0).exists()]

        for i, (nome, email, telefone) in enumerate(clientes):
            if i >= len(produtos_com_estoque):
                break

            interesse, _ = InteresseCompra.objects.get_or_create(
                email_cliente=email,
                defaults={
                    "nome_cliente": nome,
                    "telefone_cliente": telefone,
                },
            )

            produto = produtos_com_estoque[i]
            variacao = produto.variacoes.filter(estoque__gt=0).first()

            ordem, created = OrdemCompra.objects.get_or_create(
                interesse=interesse,
                defaults={
                    "numero": f"OC-{2024}{str(i+1).zfill(4)}",
                    "nome_cliente": interesse.nome_cliente,
                    "email_cliente": interesse.email_cliente,
                    "telefone_cliente": interesse.telefone_cliente,
                    "status": StatusOrdemCompra.PENDENTE_APROVACAO,
                    "observacoes": f"Interesse em {produto.produto}",
                },
            )

            if created:
                ItemOrdemCompra.objects.create(
                    ordem=ordem,
                    produto=produto,
                    variacao=variacao,
                    quantidade=1,
                    preco_unitario=variacao.preco if variacao else produto.preco,
                )

        self.stdout.write(f"    {OrdemCompra.objects.count()} ordens de compra criadas")

    def _mostrar_resumo(self):
        """Mostra resumo dos dados criados"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("RESUMO DOS DADOS CRIADOS:")
        self.stdout.write("=" * 50)
        self.stdout.write(f"  Categorias: {Categoria.objects.count()}")
        self.stdout.write(f"  Atributos: {Atributo.objects.count()}")
        self.stdout.write(f"  Valores de Atributos: {ValorAtributo.objects.count()}")
        self.stdout.write(f"  Produtos: {Produto.objects.count()}")
        self.stdout.write(f"  Variações: {VariacaoProduto.objects.count()}")
        self.stdout.write(f"  Inventários: {Inventario.objects.count()}")
        self.stdout.write(f"  Movimentações: {Estoque.objects.count()}")
        self.stdout.write(f"  Ordens de Compra: {OrdemCompra.objects.count()}")
        self.stdout.write("=" * 50)
