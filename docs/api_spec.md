# Especificação Técnica da API REST - PIZZARIA Fellice

Esta documentação descreve todos os endpoints da API desenvolvida em **FastAPI**, com padrões de autenticação JWT, modelos Pydantic de entrada/saída e códigos de retorno HTTP.

---

## 1. Padrões Globais

- **Base URL**: `/api/v1`
- **Autenticação**: Header `Authorization: Bearer <token_jwt>`
- **Códigos de Resposta**:
  - `200 OK`: Consulta ou atualização bem-sucedida.
  - `201 Created`: Criação de recurso concluída.
  - `400 Bad Request`: Erro de validação ou regra de negócio violada.
  - `401 Unauthorized`: Token ausente, inválido ou expirado.
  - `403 Forbidden`: Usuário não possui privilégios para a ação ou para a loja indicada.
  - `404 Not Found`: Recurso não encontrado.
  - `422 Unprocessable Entity`: Erro de formato de schema Pydantic.

---

## 2. Endpoints por Módulo

### 2.1 Autenticação (`/auth`)

#### `POST /api/v1/auth/login`
- **Descrição**: Autentica o usuário e emite o token JWT.
- **Request Body**:
  ```json
  {
    "email": "gerente.tatuape@fellice.com.br",
    "senha": "senhaSegura123"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": 2,
      "nome": "Carlos Gerente",
      "email": "gerente.tatuape@fellice.com.br",
      "role": "GERENTE",
      "loja_id": 1,
      "loja_nome": "Fellice Tatuapé"
    }
  }
  ```

#### `GET /api/v1/auth/me`
- **Descrição**: Retorna o perfil completo do usuário autenticado a partir do token.

---

### 2.2 Usuários (`/users`) - *Acesso Restrito: ADMIN*

#### `GET /api/v1/users`
- **Filtros (Query Params)**: `loja_id`, `role`, `ativo`, `skip`, `limit`
- **Response `200 OK`**: Lista paginada de usuários.

#### `POST /api/v1/users`
- **Request Body**:
  ```json
  {
    "nome": "Mariana Estoquista",
    "email": "mariana@fellice.com.br",
    "senha": "senhaTemporaria123",
    "role": "FUNCIONARIO",
    "loja_id": 1
  }
  ```

#### `PUT /api/v1/users/{id}`
- **Atualização**: Altera nome, e-mail, perfil ou filial vinculada.

#### `PATCH /api/v1/users/{id}/status`
- **Request Body**: `{"ativo": false}` (inativação do usuário).

---

### 2.3 Lojas (`/lojas`)

#### `GET /api/v1/lojas`
- **Descrição**: Lista todas as lojas ativas. Se o usuário for Gerente/Funcionário, retorna apenas sua filial vinculada.

#### `POST /api/v1/lojas` (*Apenas ADMIN*)
- **Request Body**:
  ```json
  {
    "nome": "Fellice Nhocuné",
    "codigo": "NHOCUNE",
    "endereco": "Av. Dr. Pereira Vergueiro, 500",
    "telefone": "(11) 2741-0000"
  }
  ```

#### `GET /api/v1/lojas/{id}`
- **Descrição**: Detalha informações de uma loja.

---

### 2.4 Produtos & Catálogo por Loja

#### `GET /api/v1/produtos`
- **Descrição**: Catálogo global de produtos cadastrados na rede.

#### `POST /api/v1/produtos` (*ADMIN/GERENTE*)
- **Request Body**:
  ```json
  {
    "nome": "Queijo Mussarela Peça",
    "categoria": "Laticínios",
    "unidade_medida": "KG",
    "codigo_sku": "LAT-MUS-01"
  }
  ```

#### `GET /api/v1/lojas/{loja_id}/produtos`
- **Descrição**: Lista os produtos habilitados para a filial com seus limites operacionais de estoque.

#### `POST /api/v1/lojas/{loja_id}/produtos`
- **Descrição**: Habilita um produto na filial.
- **Request Body**:
  ```json
  {
    "produto_id": 1,
    "estoque_minimo": 10.0,
    "estoque_maximo": 50.0
  }
  ```

---

### 2.5 Estoque (`/lojas/{loja_id}/estoque`)

#### `GET /api/v1/lojas/{loja_id}/estoque`
- **Descrição**: Consulta posição de estoque atual em tempo real da loja.
- **Response `200 OK`**:
  ```json
  [
    {
      "produto_id": 1,
      "produto_nome": "Queijo Mussarela Peça",
      "unidade_medida": "KG",
      "saldo_atual": 32.500,
      "estoque_minimo": 10.0,
      "estoque_maximo": 50.0,
      "alerta_reposicao": false
    }
  ]
  ```

---

### 2.6 Entradas (`/lojas/{loja_id}/entradas`)

#### `POST /api/v1/lojas/{loja_id}/entradas`
- **Descrição**: Registra nova entrada de suprimento e atualiza automaticamente o saldo do estoque.
- **Request Body**:
  ```json
  {
    "produto_id": 1,
    "quantidade_recebida": 18.0,
    "quantidade_esperada": 20.0,
    "fornecedor": "Laticínios Scala",
    "nota_fiscal": "NF-99881",
    "motivo_divergencia": "Fornecedor enviou 2kg a menos por falta de lote."
  }
  ```
- **Regra**: Se `quantidade_recebida != quantidade_esperada`, `motivo_divergencia` é obrigatório.

#### `GET /api/v1/lojas/{loja_id}/entradas`
- **Filtros**: `produto_id`, `data_inicio`, `data_fim`, `apenas_divergentes`

---

### 2.7 Contagem Diária (`/lojas/{loja_id}/contagens`)

#### `POST /api/v1/lojas/{loja_id}/contagens`
- **Descrição**: Registra a contagem física dos itens, confrontando imediatamente com o estoque esperado.
- **Request Body**:
  ```json
  {
    "data_contagem": "2026-09-14",
    "observacao_geral": "Contagem noturna realizada pós encerramento do salão",
    "itens": [
      {
        "produto_id": 1,
        "quantidade_contada": 28.5,
        "observacao": "Divergência de -4kg em relação ao esperado (uso para bordas recheadas)"
      },
      {
        "produto_id": 2,
        "quantidade_contada": 15.0,
        "observacao": null
      }
    ]
  }
  ```
- **Response `201 Created`**: Retorna os itens calculados com `quantidade_esperada`, `diferenca` e alerta de divergência.

---

### 2.8 Fechamento de Turno (`/lojas/{loja_id}/fechamentos`)

#### `POST /api/v1/lojas/{loja_id}/fechamentos/iniciar`
- **Request Body**:
  ```json
  {
    "data_fechamento": "2026-09-14",
    "turno": "NOITE"
  }
  ```

#### `POST /api/v1/fechamentos/{id}/finalizar`
- **Descrição**: Consolida a contagem física, totaliza entradas e congela o snapshot em `fechamento_itens`.
- **Efeito colateral**: Bloqueia alterações futuras nos registros deste turno.

#### `POST /api/v1/fechamentos/{id}/reabrir` (*ADMIN/GERENTE*)
- **Request Body**:
  ```json
  {
    "justificativa": "Correção autorizada pela diretoria devido a erro de digitação na farinha."
  }
  ```
- **Efeito colateral**: Registrado obrigatoriamente no log de auditoria.

---

### 2.9 Auditoria (`/auditoria`) - *Apenas ADMIN*

#### `GET /api/v1/auditoria`
- **Filtros**: `usuario_id`, `loja_id`, `entidade`, `acao`, `data_inicio`, `data_fim`
- **Response `200 OK`**: Lista cronológica de ações com diff de estado antigo e novo.

---

### 2.10 Relatórios e Dashboard

#### `GET /api/v1/dashboard/kpis`
- **Descrição**: Indicadores principais (Lojas ativas, total de perdas na semana, fechamentos pendentes de hoje).

#### `GET /api/v1/relatorios/semanal?loja_id=1`
- **Descrição**: Balanço de entradas, contagens e perdas consolidadas por semana.

#### `GET /api/v1/relatorios/divergencias?dias=7`
- **Descrição**: Ranking dos insumos com maior quebra ou perda no período.

#### `GET /api/v1/relatorios/comparativo-lojas` (*Apenas ADMIN*)
- **Descrição**: Tabela comparativa de desempenho e perdas entre filiais (Tatuapé, Aricanduva, Nhocuné).
