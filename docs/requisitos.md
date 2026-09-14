# Documento de Requisitos de Software (SRS) - PIZZARIA Fellice

Este documento especifica os Requisitos Funcionais (RF), Regras de Negócio (RN) e Requisitos Não Funcionais (RNF) para o sistema de controle de estoque, gestão de entradas, contagem física e fechamento operacional das filiais da **PIZZARIA Fellice** (Tatuapé, Aricanduva, Nhocuné e expansões).

---

## 1. Visão Geral do Sistema

O sistema tem como objetivo mitigar desvios, desperdícios e falta de insumos através do acompanhamento rigoroso do estoque diário por filial. O sistema viabiliza:
- Autenticação e autorização baseada em papéis (RBAC).
- Gestão de múltiplos catálogos de produtos por loja.
- Controle de entradas com alerta de divergência entre pedido e entrega física.
- Rotina de contagem física com apuração imediata de sobras e quebras.
- Fechamento de turnos com blindagem e congelamento de dados.
- Rastreabilidade total através de logs de auditoria.
- Inteligência operacional com relatórios comparativos entre filiais.

---

## 2. Perfis de Usuário (Atores)

1. **Administrador (`ADMIN`)**:
   - Acesso irrestrito a todas as lojas e configurações do sistema.
   - Gestão de usuários, filiais e parâmetros globais.
   - Acesso a auditoria e relatórios consolidados/comparativos.
   - Permissão para reabrir fechamentos com justificativa.

2. **Gerente (`GERENTE`)**:
   - Gestão operacional da sua filial vinculada.
   - Lançamento e validação de entradas, contagens e fechamentos.
   - Visualização de relatórios analíticos da sua filial.

3. **Funcionário (`FUNCIONARIO`)**:
   - Operação diária da sua filial vinculada.
   - Lançamento de entradas físicas de produtos.
   - Preenchimento da contagem física de estoque.

---

## 3. Requisitos Funcionais (RF)

### 3.1 Módulo: Autenticação e Usuários
- **RF01 - Autenticação por Credenciais**: O sistema deve autenticar usuários via e-mail e senha, retornando um token de acesso JWT com tempo de expiração configurável.
- **RF02 - Encerramento de Sessão**: O sistema deve permitir o logout do usuário.
- **RF03 - Cadastro de Usuários**: Apenas Administradores podem cadastrar novos usuários definindo nome, e-mail, perfil e filial de atuação.
- **RF04 - Gestão de Perfis de Acesso**: O sistema deve suportar exatamente três papéis: `ADMIN`, `GERENTE`, `FUNCIONARIO`.
- **RF05 - Vínculo com Filial**: Usuários do tipo `GERENTE` e `FUNCIONARIO` devem obrigatoriamente possuir uma `loja_id` vinculada. Usuários `ADMIN` possuem `loja_id = null`, podendo operar e filtrar qualquer loja.
- **RF06 - Redefinição e Alteração de Senha**: O sistema deve permitir que Administradores redefinam senhas e que o próprio usuário altere sua senha.

### 3.2 Módulo: Lojas (Filiais)
- **RF07 - Cadastro de Lojas**: O sistema deve permitir o cadastro de filiais contendo nome, código de identificação, endereço, telefone e status.
- **RF08 - Listagem de Lojas**: O sistema deve listar as lojas ativas. Administradores podem alternar o contexto de visualização entre filiais.
- **RF09 - Inativação de Filiais**: O sistema deve permitir inativar lojas sem perder o histórico transacional.

### 3.3 Módulo: Produtos e Catálogo por Loja
- **RF10 - Cadastro Global de Produtos**: O sistema deve permitir o cadastro de insumos com nome, categoria, código SKU e unidade de medida (`KG`, `L`, `UN`, `G`, `ML`, `CX`, `PC`).
- **RF11 - Edição e Inativação**: O sistema deve permitir editar informações e inativar produtos globalmente.
- **RF12 - Catálogo Personalizado por Loja**: O sistema deve permitir associar quais produtos do catálogo global estão disponíveis em cada filial, permitindo estoques mínimos e máximos distintos por loja.

### 3.4 Módulo: Estoque
- **RF13 - Consulta de Saldo em Tempo Real**: O sistema deve exibir a posição de estoque atualizada para cada item da loja.
- **RF14 - Atualização Automática**: O saldo em estoque deve ser incrementado automaticamente na confirmação de entradas e atualizado na conclusão do fechamento diário.
- **RF15 - Precisão Fracionária**: O sistema deve suportar quantidades decimais com até 3 casas decimais (ex: 2.350 kg de queijo, 1.500 L de azeite).

### 3.5 Módulo: Entradas de Mercadorias
- **RF16 - Registro de Entrada**: O operador deve registrar entradas informando: produto, quantidade recebida, quantidade esperada (da nota/pedido), fornecedor (opcional), número da nota fiscal (opcional).
- **RF17 - Cálculo de Divergência de Entrada**: O sistema deve calcular automaticamente a diferença entre quantidade esperada e quantidade recebida.
- **RF18 - Alerta de Divergência**: Quando `quantidade_recebida != quantidade_esperada`, o sistema deve marcar a entrada como divergente e exigir a justificativa/observação.
- **RF19 - Histórico Filtrado**: O sistema deve permitir filtrar o histórico de entradas por período, produto e fornecedor.

### 3.6 Módulo: Contagem Diária / Física
- **RF20 - Interface de Contagem Física**: O operador deve registrar a quantidade física contada no final do turno ou dia.
- **RF21 - Comparação Automática**: O sistema deve resgatar o estoque esperado (saldo lógico no momento) e confrontar com a quantidade contada.
- **RF22 - Apuração de Diferenças**: O sistema deve calcular a diferença: `diferenca = quantidade_contada - estoque_esperado`.
- **RF23 - Obrigatoriedade de Justificativa**: Caso haja diferença positiva ou negativa, o preenchimento do campo de observação é obrigatório.

### 3.7 Módulo: Fechamento de Turno / Diário
- **RF24 - Sessão de Fechamento**: O sistema deve permitir abrir um fechamento informando data e turno (`DIA`, `NOITE`, `UNICO`).
- **RF25 - Snapshot Consolidado (`fechamento_itens`)**: No fechamento, o sistema deve gravar uma fotografia congelada de:
  - Saldo inicial do turno.
  - Total de entradas ocorridas no turno.
  - Saldo final apurado na contagem física.
  - Perda/Divergência calculada.
- **RF26 - Bloqueio de Edição**: Após a finalização do fechamento, todas as movimentações e contagens daquele turno ficam congeladas para edição.
- **RF27 - Reabertura Controlada**: Apenas Administradores ou Gerentes autorizados podem reabrir um fechamento, exigindo motivo formal registrado em auditoria.

### 3.8 Módulo: Histórico e Auditoria
- **RF28 - Log de Ações Sensíveis**: O sistema deve registrar de forma indelével: usuário, IP, entidade, ID do registro, tipo de ação (`CRIACAO`, `EDICAO`, `EXCLUSAO`, `FECHAMENTO`, `REABERTURA`) e estado anterior/novo dos dados em formato JSON.
- **RF29 - Consulta de Auditoria**: O Administrador deve poder filtrar logs por data, usuário, filial e entidade.

### 3.9 Módulo: Relatórios e Dashboards
- **RF30 - Relatório Semanal Consolidado**: Visão agregada por loja de movimentações, quebras e entradas dos últimos 7 dias.
- **RF31 - Relatório de Divergências e Perdas**: Ranking de produtos com maior desperdício/quebra e valor financeiro estimado.
- **RF32 - Relatório Comparativo Entre Lojas**: Visão multi-lojas para comparar índices de perda e consumo entre Tatuapé, Aricanduva, Nhocuné, etc.
- **RF33 - Dashboard de Indicadores (KPIs)**: Painel com resumo de lojas ativas, fechamentos pendentes no dia, alertas de divergência em aberto e perdas da semana.

---

## 4. Regras de Negócio (RN)

- **RN01 - Isolamento Multi-Loja**: Um usuário com perfil `FUNCIONARIO` ou `GERENTE` só pode visualizar e modificar dados da sua própria loja. Qualquer tentativa de manipular outra loja deve retornar status `403 Forbidden`.
- **RN02 - Imutabilidade Pós-Fechamento**: Nenhum item de contagem ou entrada pertencente a um turno com fechamento `FINALIZADO` pode ser alterado diretamente sem a reabertura formal do fechamento.
- **RN03 - Obrigatoriedade de Justificativa em Divergências**: Se `quantidade_recebida != quantidade_esperada` na entrada, ou `quantidade_contada != estoque_esperado` na contagem, o campo `observacao` não pode ser vazio.
- **RN04 - Exclusão Lógica (Soft Delete)**: Lojas, produtos e usuários não são excluídos fisicamente se possuírem registros correlatos de estoque ou movimentação.
- **RN05 - Integridade de Catálogo**: Uma entrada ou contagem só pode ser lançada para produtos que estejam explicitamente vinculados e ativos no catálogo da respectiva filial (`loja_produtos`).
- **RN06 - Responsabilização Obrigatória**: Todas as transações (entradas, contagens, fechamentos) devem armazenar a chave estrangeira do usuário logado que executou a operação.

---

## 5. Requisitos Não Funcionais (RNF)

- **RNF01 - Portabilidade de Banco de Dados**: A aplicação deve utilizar SQLAlchemy 2.0 com ORM desacoplado, sendo 100% compatível com SQLite (desenvolvimento) e PostgreSQL/CockroachDB (produção) via configuração de `DATABASE_URL`.
- **RNF02 - Segurança de Senhas**: As senhas devem ser armazenadas com hash forte via `bcrypt`.
- **RNF03 - Segurança de Comunicação**: A API deve trafegar dados protegidos por autenticação JWT (JSON Web Tokens) com algoritmo `HS256`.
- **RNF04 - Tempo de Resposta**: Endpoints de consulta e gravação transacional devem responder em menos de 200ms sob condições normais de rede local.
- **RNF05 - Documentação Automática**: A API deve expor documentação Swagger/OpenAPI interativa e atualizada automaticamente em `/docs` e Redoc em `/redoc`.
