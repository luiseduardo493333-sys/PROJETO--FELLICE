# 🍕 Pizzaria Fellice - Sistema de Controle Operacional & Estoque

Sistema completo de gestão de estoque, controle de entradas de insumos, conferência de divergências, contagem física diária, fechamento de turnos blindado, trilha de auditoria e relatórios consolidados para a rede **Pizzaria Fellice** (unidades Tatuapé, Aricanduva, Nhocuné e futuras filiais).

---

## 🚀 Tecnologias Utilizadas

- **Backend**: Python 3.10+ / FastAPI (arquitetura híbrida MVC Web + API REST JSON).
- **Banco de Dados**: SQLAlchemy 2.0 com suporte transparente para **SQLite** (ambiente local) e migração para **PostgreSQL** ou **CockroachDB** via variável `DATABASE_URL`.
- **Autenticação & Segurança**: JWT (JSON Web Tokens) com hashing seguro `bcrypt` e RBAC (*Role-Based Access Control*).
- **Frontend / Camada de Apresentação**: Templates Jinja2 com interface moderna, responsiva e paleta alinhada ao padrão corporativo da marca.
- **Auditoria**: Log indelével gravado em JSON registrando autor, entidade, dados anteriores e novos.
- **Testes**: Pytest e FastAPI TestClient com 100% de aprovação no ciclo de regras de negócio.

---

## 📋 Módulos e Regras de Negócio Implementadas

1. **Autenticação & RBAC**:
   - `ADMINISTRADOR`: Acesso global, relatórios comparativos, auditoria e reabertura de turnos.
   - `GERENTE`: Operação da sua filial vinculada (entradas, validação de contagens, fechamento de turno).
   - `FUNCIONARIO`: Operação diária da filial vinculada (digitação de contagem e recebimento de mercadorias).
2. **Lojas / Filiais**:
   - Cadastro e gestão das unidades Tatuapé, Aricanduva, Nhocuné e seletor de contexto de filial.
3. **Catálogo de Produtos & Insumos**:
   - Insumos parametrizados com unidades de medida (`KG`, `L`, `UN`, `CX`, etc.), estoque mínimo e máximo por loja.
4. **Posição de Estoque em Tempo Real**:
   - Saldos calculados automaticamente a partir de entradas e reconciliações de contagens físicas.
5. **Entradas & Recebimento de Mercadorias**:
   - Comparação automática entre quantidade recebida e quantidade da nota/pedido.
   - **Alerta obrigatório de divergência**: Exige preenchimento de justificativa quando há divergência física.
6. **Contagem Diária / Física**:
   - Interface rápida para conferência física com cálculo automático: `diferenca = contado - esperado`.
7. **Fechamento de Turno Blindado**:
   - Geração de snapshot histórico em `fechamento_itens` e **bloqueio de alterações posteriores** sem autorização.
   - Reabertura permitida exclusivamente com registro de justificativa na auditoria.
8. **Trilha de Auditoria & Rastreabilidade**:
   - Histórico permanente com filtros por entidade e ação.
9. **Relatórios & Inteligência**:
   - Balanço semanal de insumos recebidos, ranking de perdas e desperdícios, e comparativo de indicadores entre lojas.
10. **API REST JSON (`/api/v1`)**:
    - Endpoints padronizados para integração mobile, PDV e sistemas legados.

---

## 📦 Como Executar o Projeto

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente
O arquivo `.env` já vem pré-configurado para SQLite local:
```ini
PROJECT_NAME="Pizzaria Fellice - Controle de Estoque"
SECRET_KEY="fellice-super-secret-key-change-in-production-random-jwt-token"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=480
DATABASE_URL="sqlite:///./fellice.db"
```

### 3. Popular Banco de Dados (Seed Inicial)
Execute o script para criar as filiais, produtos básicos de pizzaria e usuários padrão:
```bash
python scripts/seed_data.py
```

### 4. Iniciar o Servidor FastAPI
```bash
uvicorn app.main:app --reload
```
Acesse no navegador:
- **Painel Web**: [http://localhost:8000](http://localhost:8000)
- **Documentação Swagger / OpenAPI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentação Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔑 Usuários e Credenciais de Teste

| Perfil | E-mail (Login) | Senha | Filial Vinculada |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin@fellice.com.br` | `admin123` | Global (Todas as filiais) |
| **Gerente Tatuapé** | `gerente.tatuape@fellice.com.br` | `gerente123` | Fellice Tatuapé |
| **Funcionário Tatuapé** | `funcionario.tatuape@fellice.com.br` | `func123` | Fellice Tatuapé |
| **Gerente Aricanduva** | `gerente.aricanduva@fellice.com.br` | `gerente123` | Fellice Aricanduva |
| **Gerente Nhocuné** | `gerente.nhocune@fellice.com.br` | `gerente123` | Fellice Nhocuné |

---

## 🧪 Como Rodar os Testes Automatizados

```bash
python -m pytest -v
```
Todos os 11 testes automatizados cobrem autenticação, bloqueio RBAC, atualização automática de estoque, alerta de divergências em entradas, contagens e fechamentos de turno com auditoria.
