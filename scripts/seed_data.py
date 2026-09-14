"""
Script de carga inicial (Seed) de dados para a PIZZARIA Fellice.
Popula as filiais (Tatuapé, Aricanduva, Nhocuné), usuários com perfis RBAC,
catálogo completo de insumos de pizzaria, saldos de estoque e histórico inicial.
"""
import sys
from pathlib import Path

# Adiciona raiz do projeto ao path para importar 'app'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone, timedelta
from app.database import Session, engine, Base
from app.auth import hash_senha
from app.models.loja import Loja
from app.models.usuario import Usuario, RoleEnum
from app.models.produto import Produto, UnidadeMedidaEnum
from app.models.estoque import LojaProduto
from app.models.entrada import Entrada
from app.models.contagem import Contagem, ContagemItem
from app.models.fechamento import Fechamento, FechamentoItem, StatusFechamentoEnum, TurnoEnum
from app.models.audit import AuditLog


def popular_dados():
    print("Criando tabelas...")
    Base.metadata.create_all(bind=engine)
    db = Session()

    try:
        # 1. LOJAS / FILIAIS
        lojas_dados = [
            {
                "nome": "Fellice Tatuapé",
                "codigo": "TATUAPE",
                "endereco": "Rua Tuiuti, 1850 - Tatuapé, São Paulo - SP",
                "telefone": "(11) 2091-1010",
            },
            {
                "nome": "Fellice Aricanduva",
                "codigo": "ARICANDUVA",
                "endereco": "Av. Aricanduva, 5555 - Aricanduva, São Paulo - SP",
                "telefone": "(11) 2721-2020",
            },
            {
                "nome": "Fellice Nhocuné",
                "codigo": "NHOCUNE",
                "endereco": "Av. Dr. Pereira de Vergueiro, 120 - Vila Nhocuné, São Paulo - SP",
                "telefone": "(11) 2741-3030",
            },
        ]

        lojas_db = {}
        for l in lojas_dados:
            loja = db.query(Loja).filter(Loja.codigo == l["codigo"]).first()
            if not loja:
                loja = Loja(**l, ativa=True)
                db.add(loja)
                db.commit()
                db.refresh(loja)
                print(f"Loja criada: {loja.nome}")
            lojas_db[l["codigo"]] = loja

        # 2. USUÁRIOS (RBAC)
        usuarios_dados = [
            {
                "nome": "Administrador Geral Fellice",
                "email": "admin@fellice.com.br",
                "senha": "admin123",
                "role": RoleEnum.ADMIN,
                "loja_id": None,
            },
            {
                "nome": "Carlos Gerente Tatuapé",
                "email": "gerente.tatuape@fellice.com.br",
                "senha": "gerente123",
                "role": RoleEnum.GERENTE,
                "loja_id": lojas_db["TATUAPE"].id,
            },
            {
                "nome": "Marcos Pizzaiolo / Funcionário",
                "email": "funcionario.tatuape@fellice.com.br",
                "senha": "func123",
                "role": RoleEnum.FUNCIONARIO,
                "loja_id": lojas_db["TATUAPE"].id,
            },
            {
                "nome": "Fernanda Gerente Aricanduva",
                "email": "gerente.aricanduva@fellice.com.br",
                "senha": "gerente123",
                "role": RoleEnum.GERENTE,
                "loja_id": lojas_db["ARICANDUVA"].id,
            },
            {
                "nome": "Roberto Gerente Nhocuné",
                "email": "gerente.nhocune@fellice.com.br",
                "senha": "gerente123",
                "role": RoleEnum.GERENTE,
                "loja_id": lojas_db["NHOCUNE"].id,
            },
        ]

        usuarios_db = {}
        for u in usuarios_dados:
            usuario = db.query(Usuario).filter(Usuario.email == u["email"]).first()
            if not usuario:
                usuario = Usuario(
                    nome=u["nome"],
                    email=u["email"],
                    senha_hash=hash_senha(u["senha"]),
                    role=u["role"],
                    loja_id=u["loja_id"],
                    ativo=True,
                )
                db.add(usuario)
                db.commit()
                db.refresh(usuario)
                print(f"Usuário criado: {usuario.nome} ({usuario.email}) - {usuario.role.value}")
            usuarios_db[u["email"]] = usuario

        # 3. PRODUTOS / INSUMOS (TODOS EM UNIDADE - UN)
        produtos_dados = [
            {"nome": "Queijo Mussarela Peça", "categoria": "Laticínios", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-MUS-01"},
            {"nome": "Molho de Tomate Especial", "categoria": "Molhos & Temperos", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-MOL-01"},
            {"nome": "Farinha de Trigo Especial 00", "categoria": "Farinhas & Massas", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-FAR-01"},
            {"nome": "Linguiça Calabresa Defumada", "categoria": "Carnes & Embutidos", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-CAL-01"},
            {"nome": "Requeijão Cremoso Bisnaga", "categoria": "Laticínios", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-CAT-01"},
            {"nome": "Presunto Cozido Especial", "categoria": "Carnes & Embutidos", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-PRE-01"},
            {"nome": "Azeitona Preta Fatiada", "categoria": "Conservas", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-AZE-01"},
            {"nome": "Orégano Desidratado Puro", "categoria": "Molhos & Temperos", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-ORE-01"},
            {"nome": "Caixa de Pizza Grande 35cm", "categoria": "Embalagens", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-CXG-01"},
            {"nome": "Caixa de Pizza Broto 25cm", "categoria": "Embalagens", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-CXB-01"},
            {"nome": "Refrigerante Coca-Cola 350ml", "categoria": "Bebidas", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-BEB-01"},
            {"nome": "Cerveja Heineken Long Neck 330ml", "categoria": "Bebidas", "unidade_medida": UnidadeMedidaEnum.UN, "codigo_sku": "SKU-BEB-02"},
        ]

        produtos_db = []
        for p in produtos_dados:
            produto = db.query(Produto).filter(Produto.nome == p["nome"]).first()
            if not produto:
                produto = Produto(**p, ativo=True)
                db.add(produto)
                db.commit()
                db.refresh(produto)
                print(f"Produto criado: {produto.nome}")
            else:
                produto.unidade_medida = UnidadeMedidaEnum.UN
                db.commit()
            produtos_db.append(produto)

        # 4. CATÁLOGO DAS LOJAS E SALDOS DE ESTOQUE (EM UNIDADES)
        saldos_padrao = {
            "Queijo Mussarela Peça": (45.0, 15.0, 80.0),
            "Molho de Tomate Especial": (32.0, 10.0, 60.0),
            "Farinha de Trigo Especial 00": (85.0, 25.0, 150.0),
            "Linguiça Calabresa Defumada": (28.0, 8.0, 50.0),
            "Requeijão Cremoso Bisnaga": (18.0, 6.0, 40.0),
            "Presunto Cozido Especial": (14.0, 5.0, 30.0),
            "Azeitona Preta Fatiada": (8.0, 3.0, 20.0),
            "Orégano Desidratado Puro": (3.0, 1.0, 8.0),
            "Caixa de Pizza Grande 35cm": (250.0, 50.0, 500.0),
            "Caixa de Pizza Broto 25cm": (120.0, 30.0, 250.0),
            "Refrigerante Coca-Cola 350ml": (96.0, 24.0, 200.0),
            "Cerveja Heineken Long Neck 330ml": (48.0, 12.0, 100.0),
        }

        for loja in lojas_db.values():
            for prod in produtos_db:
                lp = (
                    db.query(LojaProduto)
                    .filter(LojaProduto.loja_id == loja.id, LojaProduto.produto_id == prod.id)
                    .first()
                )
                if not lp:
                    saldo, est_min, est_max = saldos_padrao.get(prod.nome, (10.0, 5.0, 50.0))
                    # Variando um pouco por loja para dados mais realistas
                    if loja.codigo == "ARICANDUVA":
                        saldo = round(saldo * 0.85, 1)
                    elif loja.codigo == "NHOCUNE":
                        saldo = round(saldo * 0.70, 1)

                    lp = LojaProduto(
                        loja_id=loja.id,
                        produto_id=prod.id,
                        saldo_atual=saldo,
                        estoque_minimo=est_min,
                        estoque_maximo=est_max,
                        ativo=True,
                    )
                    db.add(lp)
            db.commit()
        print("Catálogo e saldos vinculados a todas as lojas.")

        # 5. ENTRADAS DE AMOSTRA (Regular e Divergente)
        loja_tat = lojas_db["TATUAPE"]
        usr_gerente = usuarios_db["gerente.tatuape@fellice.com.br"]
        prod_mus = db.query(Produto).filter(Produto.nome.like("%Mussarela%")).first()
        prod_farinha = db.query(Produto).filter(Produto.nome.like("%Farinha%")).first()

        entradas_existentes = db.query(Entrada).count()
        if entradas_existentes == 0 and prod_mus and prod_farinha:
            # Entrada 1: Regular
            e1 = Entrada(
                loja_id=loja_tat.id,
                produto_id=prod_mus.id,
                usuario_id=usr_gerente.id,
                quantidade_recebida=30.0,
                quantidade_esperada=30.0,
                diferenca=0.0,
                divergente=False,
                fornecedor="Laticínios Scala Distribuidora",
                nota_fiscal="NF-89210",
                data_entrada=datetime.now(timezone.utc) - timedelta(days=2),
            )
            # Entrada 2: Divergente (recebeu a menos que a NF)
            e2 = Entrada(
                loja_id=loja_tat.id,
                produto_id=prod_farinha.id,
                usuario_id=usr_gerente.id,
                quantidade_recebida=45.0,
                quantidade_esperada=50.0,
                diferenca=-5.0,
                divergente=True,
                motivo_divergencia="Fornecedor entregou 9 sacos de 5kg em vez de 10 sacos. Falta anotada no canhoto da NF.",
                fornecedor="Moinho Paulista S/A",
                nota_fiscal="NF-45812",
                data_entrada=datetime.now(timezone.utc) - timedelta(days=1),
            )
            db.add_all([e1, e2])
            db.commit()
            print("Entradas de amostra registradas com sucesso.")

        # 6. CONTAGEM FÍSICA DE AMOSTRA
        contagens_existentes = db.query(Contagem).count()
        if contagens_existentes == 0 and prod_mus:
            c = Contagem(
                loja_id=loja_tat.id,
                usuario_id=usr_gerente.id,
                data_contagem=datetime.now(timezone.utc) - timedelta(hours=5),
                finalizada=True,
                observacao_geral="Contagem de rotina do início do turno.",
            )
            db.add(c)
            db.commit()
            db.refresh(c)

            item_c = ContagemItem(
                contagem_id=c.id,
                produto_id=prod_mus.id,
                quantidade_esperada=48.0,
                quantidade_contada=45.0,
                diferenca=-3.0,
                divergente=True,
                observacao="Desperdício no ralo de preparação e fatiamento.",
            )
            db.add(item_c)
            db.commit()
            print("Contagem física de amostra registrada.")

        # 7. FECHAMENTO DE TURNO DE AMOSTRA
        fechamentos_existentes = db.query(Fechamento).count()
        if fechamentos_existentes == 0 and prod_mus:
            f = Fechamento(
                loja_id=loja_tat.id,
                usuario_id=usr_gerente.id,
                data_fechamento=datetime.now(timezone.utc) - timedelta(days=1),
                turno=TurnoEnum.NOITE,
                status=StatusFechamentoEnum.FINALIZADO,
                closed_at=datetime.now(timezone.utc) - timedelta(days=1, hours=1),
            )
            db.add(f)
            db.commit()
            db.refresh(f)

            item_f = FechamentoItem(
                fechamento_id=f.id,
                produto_id=prod_mus.id,
                saldo_inicial=40.0,
                total_entradas=30.0,
                contagem_final=45.5,
                diferenca=-2.5,
                observacao="Fechamento do turno noturno consolidado com sucesso.",
            )
            db.add(item_f)
            db.commit()
            print("Fechamento de turno de amostra registrado.")

        # 7. AUDITORIA INICIAL
        log_seed = AuditLog(
            usuario_id=usuarios_db["admin@fellice.com.br"].id,
            loja_id=None,
            entidade="SISTEMA",
            entidade_id=1,
            acao="SEED_INICIAL",
            dados_novos='{"mensagem": "Carga inicial da base de dados e lojas Fellice realizada com sucesso."}',
        )
        db.add(log_seed)
        db.commit()
        print("Log de auditoria inicial registrado.")

        print("\n=== CARGA INICIAL CONCLUÍDA COM SUCESSO! ===")
        print("Credenciais de Teste:")
        print("1. Administrador:")
        print("   Login: admin@fellice.com.br | Senha: admin123")
        print("2. Gerente Tatuapé:")
        print("   Login: gerente.tatuape@fellice.com.br | Senha: gerente123")
        print("3. Funcionário Tatuapé:")
        print("   Login: funcionario.tatuape@fellice.com.br | Senha: func123")
        print("4. Gerente Aricanduva:")
        print("   Login: gerente.aricanduva@fellice.com.br | Senha: gerente123")
        print("5. Gerente Nhocuné:")
        print("   Login: gerente.nhocune@fellice.com.br | Senha: gerente123")

    except Exception as e:
        db.rollback()
        print(f"Erro ao popular banco de dados: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    popular_dados()
