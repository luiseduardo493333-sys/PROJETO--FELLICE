import pytest
from fastapi import status
from app.database import Session
from app.models.loja import Loja
from app.models.produto import Produto
from app.models.estoque import LojaProduto
from app.models.entrada import Entrada


def test_rbac_restricao_funcionario(client, funcionario_token):
    """Funcionário não pode acessar painel de usuários ou trilha de auditoria."""
    client.cookies.set("access_token", funcionario_token)

    # Acesso a usuários é restrito ao Admin
    resp_users = client.get("/usuarios")
    assert resp_users.status_code == status.HTTP_403_FORBIDDEN

    # Acesso a auditoria é restrito ao Admin
    resp_audit = client.get("/auditoria")
    assert resp_audit.status_code == status.HTTP_403_FORBIDDEN


def test_atualizacao_automatica_estoque_com_entrada(client, gerente_token):
    """Ao registrar entrada de mercadoria, o saldo em estoque da filial deve ser incrementado."""
    client.cookies.set("access_token", gerente_token)

    db = Session()
    try:
        loja_tat = db.query(Loja).filter(Loja.codigo == "TATUAPE").first()
        produto_mussarela = db.query(Produto).filter(Produto.nome.like("%Mussarela%")).first()
        loja_prod = (
            db.query(LojaProduto)
            .filter(LojaProduto.loja_id == loja_tat.id, LojaProduto.produto_id == produto_mussarela.id)
            .first()
        )
        saldo_anterior = loja_prod.saldo_atual
    finally:
        db.close()

    # Registra entrada de 10.5 kg de mussarela
    qtd_entrada = 10.5
    response = client.post(
        "/entradas/novo",
        data={
            "loja_id": loja_tat.id,
            "produto_id": produto_mussarela.id,
            "quantidade_recebida": qtd_entrada,
            "quantidade_esperada": qtd_entrada,
            "fornecedor": "Laticínios Teste",
            "nota_fiscal": "NF-9999",
        },
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_302_FOUND

    # Verifica se o saldo foi incrementado exatamente
    db = Session()
    try:
        loja_prod_atualizado = (
            db.query(LojaProduto)
            .filter(LojaProduto.loja_id == loja_tat.id, LojaProduto.produto_id == produto_mussarela.id)
            .first()
        )
        assert round(loja_prod_atualizado.saldo_atual, 3) == round(saldo_anterior + qtd_entrada, 3)
    finally:
        db.close()


def test_alerta_divergencia_entrada(client, gerente_token):
    """Entrada com quantidade divergente da esperada exige justificativa."""
    client.cookies.set("access_token", gerente_token)

    db = Session()
    try:
        loja_tat = db.query(Loja).filter(Loja.codigo == "TATUAPE").first()
        produto = db.query(Produto).first()
    finally:
        db.close()

    # Tentativa de lançar entrada divergente sem motivo deve retornar erro 400
    response = client.post(
        "/entradas/novo",
        data={
            "loja_id": loja_tat.id,
            "produto_id": produto.id,
            "quantidade_recebida": 20.0,
            "quantidade_esperada": 25.0, # Divergente em -5
            "motivo_divergencia": "",     # Vazio!
            "fornecedor": "Distribuidora Falha",
        },
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Divergência detectada" in response.text


def test_contagem_fisica_apuracao_diferenca(client, gerente_token):
    """Contagem física calcula a diferença lógica vs física e exige justificativa em quebras."""
    client.cookies.set("access_token", gerente_token)

    db = Session()
    try:
        loja_tat = db.query(Loja).filter(Loja.codigo == "TATUAPE").first()
        produto = db.query(Produto).first()
        loja_prod = (
            db.query(LojaProduto)
            .filter(LojaProduto.loja_id == loja_tat.id, LojaProduto.produto_id == produto.id)
            .first()
        )
        saldo_sistema = loja_prod.saldo_atual
    finally:
        db.close()

    contagem_fisica = saldo_sistema - 3.0 # Faltando 3kg/unidades

    response = client.post(
        "/contagens/novo",
        data={
            "loja_id": loja_tat.id,
            "observacao_geral": "Auditoria de contagem para teste",
            f"prod_{produto.id}": contagem_fisica,
            f"obs_{produto.id}": "Avaria e quebra na linha de produção",
        },
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_302_FOUND


def test_api_rest_endpoints(client, admin_token):
    """Testa endpoints da API REST em /api/v1/."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Listagem de lojas
    r_lojas = client.get("/api/v1/lojas", headers=headers)
    assert r_lojas.status_code == status.HTTP_200_OK
    assert len(r_lojas.json()) >= 3

    # Listagem de produtos
    r_prods = client.get("/api/v1/produtos", headers=headers)
    assert r_prods.status_code == status.HTTP_200_OK
    assert len(r_prods.json()) >= 10

    # KPIs Dashboard
    r_kpis = client.get("/api/v1/dashboard/kpis", headers=headers)
    assert r_kpis.status_code == status.HTTP_200_OK
    kpis = r_kpis.json()
    assert "total_lojas" in kpis
    assert "total_produtos" in kpis
    assert "status_lojas_fechamento" in kpis
