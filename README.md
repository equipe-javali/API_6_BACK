<span id="topo">
<h1 align='center'>
:boar: EQUIPE JAVALI :boar:

APRENDIZAGEM POR PROJETOS INTEGRADOS

BACK-END
</h1>

<h1 align='center'> :keyboard:  :keyboard: </h1>

## :mag_right: Índice
<p align='center'>
    <a href="#rotas">Rotas</a> |
    <a href="#estrutura">Estrutura</a>  |
    <a href="#requisitos">Requisitos</a> |
    <a href="#execucao">Execução</a> |
    <a href="#estrategia">Estratégia de Branches</a>
</p>

<span id="rotas">

## :bust_in_silhouette: Descrição das Rotas

# Autenticação
## POST - `/token`
Rota de login, deve receber `username` e `password` e retorna o token JWT de acesso.

## GET - `/users/me/`
Rota que retorna os dados do usuário logado.

# Usuários
## GET - `/users`
Lista todos os usuários.

## GET - `/users/{id}/status-boletim`
Consulta o status de recebimento de boletim de um usuário.

## PUT - `/users/{id}/status`
Atualiza o status de recebimento de boletim.

## PUT - `/users/{id}/profile`
Atualiza os dados do perfil do usuário (email, senha, etc.). O usuário só pode atualizar seu próprio perfil.

## DELETE - `/users/{id}`
Deleta o usuário.

## GET - `/tipo/{id}`
Retorna o usuário e seu tipo (admin ou não)

→ [Voltar ao topo](#topo)

<span id="estrutura">

## :scroll: Descrição da Estrutura

```
app/
    db - arquivos
    models - modelos das tabelas
    routes - rotas
    services - serviços
    main.py - ponto inicial do projeto
```

→ [Voltar ao topo](#topo)

<span id="requisitos">

## :clipboard: Requisitos para a Execução

Para executar o projeto, certifiquece de ter instalados os seguintes programas:
* Python
* Git
    
→ [Voltar ao topo](#topo)

<span id="execucao">

## :gear: Instruções para Executar

Obtenha a permissão de uso dos modelos "google/gemma-3-1b-pt" e "google/gemma-2-2b-it" no huggingface.

```
git clone https://github.com/equipe-javali/API_6_BACK
cd API_6_BACK
python -m venv venv
.\venv\Scripts\activate
pip install -r req.txt
python .\app\main.py
```

→ [Voltar ao topo](#topo)

<span id="estrategia">

## :twisted_rightwards_arrows: Estratégia de Branches

### Padrão de branch
As branches devem seguir o padrão: Task-{numero da tarefa}

Exemplos:
- Task-1
- Task-2

### Padrão de Commit
Existem **duas formas aceitas**:  

1. **Relacionado à tarefa da branch**:  {numero da tarefa} - {descrição do que foi feito}"    

Exemplos:
- 1 - Adição da rota de cadastro de usuário
- 2 - Criação da tela de Login

2. **Baseado em tipo de commit (Conventional Commits)**: {tipo de commit} - {descrição do que foi feito}"

Exemplos:
- fix - Correção na exibição do email do usuário
- test - Adição de testes da rota de cadastro

### Tipos de Commit
* **fix** - Indica que o trecho de código commitado está solucionando um problema ou bug.
* **docs** - Indica que houve mudanças na documentação.
* **test** - Indica que houve alterações criando, alterando ou excluindo testes;
* **build** - Indica que houve alterações relacionadas a build do projeto/dependências.
* **refactor** - Indica que uma parte do código foi refatorada sem alterações nas funcionalidades.
* **ci** - Indica mudanças relacionadas a integração contínua (Continuous Integration).
* **cleanup** - Indica a remoção de código comentado ou trechos desnecessários no código-fonte.
* **remove** - Indica a exclusão de arquivos, diretórios ou funcionalidades obsoletas ou não utilizadas.

→ [Voltar ao topo](#topo)
