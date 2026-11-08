# carteira-ibovespa-scraper

Coleta a carteira teórica do dia do Ibovespa na B3, guarda a resposta bruta no MongoDB e, numa segunda etapa, trata os dados e carrega no Postgres.

```
B3 (API) --[1. collect]--> MongoDB (dado bruto) --[2. load]--> Postgres (dado tratado)
```

| Etapa | Comando | O que faz | Situação |
|---|---|---|---|
| 1. Coleta | `python -m src.pipelines.collect` | Busca a carteira na B3 e grava a resposta da API, sem alterações, na coleção `carteira_raw` | pronta |
| 2. Carga | `python -m src.pipelines.load` | Lê os documentos pendentes no MongoDB, trata e grava no Postgres | a fazer |

## Estrutura

```
src/
  config.py          # variáveis do .env e configuração do log
  pipelines/         # o que você roda, um arquivo por etapa
    collect.py       # etapa 1: B3 -> MongoDB
  sources/           # de onde os dados vêm
    b3.py            # cliente da API da B3
  storage/           # para onde os dados vão
    mongo.py
  transform/         # regras de tratamento (usadas só na etapa 2)
    portfolio.py
docker-compose.yml   # MongoDB 8 e Postgres 17
logs.conf            # formato do log
```

A coleta não interpreta o JSON da B3: ela guarda a resposta intacta e só acrescenta metadados (o que foi pedido, quando e um hash do conteúdo). Assim, uma mudança no formato da API não faz perder nenhuma coleta, e o tratamento pode ser corrigido e refeito a partir do dado bruto.

## Como rodar

Requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/), Python 3.14 e [Poetry](https://python-poetry.org/) 2.

1. Crie o `.env` a partir do modelo e preencha usuários e senhas (use só letras e números):
   ```bash
   cp .env.example .env
   ```
   As senhas só são lidas na primeira vez que os bancos sobem. Para trocá-las depois, é preciso alterá-las também dentro dos bancos.

2. Suba os bancos (com o Docker Desktop aberto):
   ```bash
   docker compose up -d
   ```

3. Instale as dependências:
   ```bash
   poetry install
   ```

4. Rode a coleta, na raiz do projeto:
   ```bash
   poetry run python -m src.pipelines.collect
   ```

Com `DRY_RUN=True` no `.env`, as etapas rodam normalmente, mas nada é gravado em nenhum banco.

## Documento gravado no MongoDB

Banco `carteira_ibovespa` (configurável em `MONGO_DB`), coleção `carteira_raw`:

```js
{
  collected_at: ISODate("..."),   // primeira vez que este conteúdo foi coletado
  last_seen_at: ISODate("..."),   // última vez que este mesmo conteúdo foi visto
  source_url: "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/",
  request_params: { language: "pt-br", pageSize: 120, index: "IBOV", segment: "2" },  // o que foi pedido à B3
  content_hash: "sha256...",      // índice único: o mesmo conteúdo nunca é gravado duas vezes
  payloads: [ { page: {...}, header: {...}, results: [...] } ],  // resposta da B3, uma por página
  processed_at: null,             // preenchido pela etapa 2 após gravar no Postgres
  processing_error: null          // motivo, se a etapa 2 não conseguir tratar o documento
}
```

## Visualizar os bancos

- **MongoDB:** [MongoDB Compass](https://www.mongodb.com/products/tools/compass), em `mongodb://localhost:27017`, com o usuário e a senha do `.env` (banco de autenticação `admin`).
- **Postgres:** [DBeaver Community](https://dbeaver.io/), em `localhost:5432`, com o banco, o usuário e a senha do `.env`.
