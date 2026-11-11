# Painel DANFE

Sistema em Django que lê os PDFs de notas fiscais eletrônicas de uma pasta, grava os dados no MySQL e mostra tudo
em um painel web: lista das notas, detalhe de cada nota (cabeçalho, emitente, destinatário, valores, impostos e
código de barras da chave de acesso) e uma tela de estatísticas.

Lê dois tipos de documento, identificados automaticamente:

- **Nota de produto (NF-e)**: o DANFE.
- **Nota de serviço (NFS-e)**: o DANFSe do padrão nacional e o modelo antigo da Prefeitura de Divinópolis
  ("Prestador de serviços / Tomador de serviços").

- **Importação automática**: a pasta é verificada a cada N segundos; PDF novo entra sozinho no painel.
- **Controle de acesso**: tela de login própria, perfis **Administrador** e **Consulta**, cadastro de usuários e troca de senha.
- **Tema claro/escuro**: botão no topo de todas as telas (inclusive no login); a escolha fica salva no navegador.
- **Front-end**: HTML + Tailwind CSS (já compilado em `static/css/app.css`) e Chart.js (em `static/js`), sem depender de CDN.

## 1. Requisitos

- Python 3.11 ou superior
- MySQL 8 (ou MariaDB 10.6+) em execução
- Node.js só é necessário se você for alterar o visual (recompilar o Tailwind)

## 2. Instalação

```bash
# dentro da pasta do projeto
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
```

Crie o banco no MySQL:

```sql
CREATE DATABASE danfe_painel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Copie `.env.example` para `.env` e ajuste usuário/senha do MySQL e a pasta das notas (`DANFE_PASTA`).
No Windows use barras normais no caminho, por exemplo `DANFE_PASTA=C:/Notas/DANFE`.

```bash
python manage.py migrate             # rode de novo sempre que atualizar o projeto
python manage.py createsuperuser     # cria o primeiro administrador
python manage.py runserver
```

Acesse http://127.0.0.1:8000 e entre com o usuário criado.

> Quer só experimentar sem MySQL? Coloque `DB_ENGINE=sqlite` no `.env`.

## 3. Notas de exemplo

A pasta `notas_pdf/` já traz 14 DANFEs e 5 notas de serviço **fictícios** (empresas, CNPJs e valores inventados)
para você ver o sistema funcionando. Para gerar outros:
`python manage.py gerar_danfes_exemplo --quantidade 20 --servico 8`.
Quando for usar as notas reais, aponte `DANFE_PASTA` para a pasta delas.

## 4. Como funciona a importação automática

| Situação | O que usar |
|---|---|
| Desenvolvimento / uso local | `python manage.py runserver` já sobe o monitor da pasta junto (`DANFE_MONITOR_AUTOSTART=1`). |
| Servidor (gunicorn, IIS etc.) | Deixe `python manage.py monitorar_pasta` rodando como serviço. |
| Agendador (cron / Agendador de Tarefas) | `python manage.py importar_notas` faz uma varredura e termina. |

- Subpastas também são lidas. Cada arquivo é identificado pelo conteúdo (hash), então renomear ou mover não duplica a nota.
- O mesmo documento salvo em dois arquivos é registrado como duplicado e fica fora dos totais.
- Arquivos que não puderam ser lidos aparecem como **Não lida** / **Leitura parcial**, com o motivo, na tela
  **Importação** (perfil Administrador), onde há o botão **Ler novamente**.

## 5. Como os documentos são lidos

`notas/leitor.py` abre o PDF, descobre o tipo e chama o leitor certo.

### Nota de produto: DANFE (`notas/danfe.py`)

1. Localiza a **chave de acesso** (44 dígitos) e confere o dígito verificador. Dela saem UF, CNPJ do emitente,
   modelo, série e número, que por isso são os campos mais confiáveis.
2. Os demais campos são lidos pela posição: para cada rótulo do DANFE (ex.: `VALOR DO ICMS`) pega-se o texto logo
   abaixo, dentro da caixa. Os rótulos aceitos, com variações de escrita, estão em `ROTULOS_VALORES`.
3. Se algum valor do bloco "Cálculo do imposto" não for achado pelo rótulo, tenta-se pela ordem das colunas.

### Nota de serviço: NFS-e (`notas/nfse.py`)

- **DANFSe (padrão nacional)**: lido por posição, como o DANFE. A chave tem 50 dígitos e também é validada.
  Neste modelo PIS/COFINS/CSLL retidos vêm somados ("Contribuições Sociais - Retidas") e são gravados em
  "Outras retenções".
- **Modelo municipal antigo**: campos no formato "Rótulo: valor". Não tem chave de acesso nem código de barras;
  a tela mostra o **código de verificação**. A nota é identificada por prestador + número + código.

Na nota de serviço o painel mostra prestador e tomador, discriminação e código do serviço, ISS (base, alíquota,
valor, retido ou não), retenções federais e valor líquido.

Limitações conhecidas:

- O leitor de DANFE foi calibrado com os DANFEs fictícios deste projeto (layout padrão retrato). Emissores diferentes
  escrevem os rótulos de formas diferentes; se uma nota real vier como "Leitura parcial", normalmente basta
  acrescentar a variação do rótulo em `ROTULOS_VALORES` e usar **Ler novamente**.
- Os leitores de NFS-e foram conferidos com notas reais de Divinópolis (os dois modelos). Prefeituras fora do
  padrão nacional têm desenhos próprios: essas notas aparecem como "Não lida" até ganharem um leitor em `nfse.py`.
- Nota cancelada recebe o selo "Cancelada", mas continua somada nos totais.
- PDF digitalizado (imagem, sem texto) não é lido; seria preciso OCR.
- Só a primeira página é lida e os itens (produtos) da nota não são importados.
- Se você tiver os **XML** das notas, a leitura por XML é exata e pode substituir a leitura do PDF.

## 6. Perfis de acesso

| Tela | Consulta | Administrador |
|---|---|---|
| Notas fiscais, detalhe, PDF original | sim | sim |
| Estatísticas | sim | sim |
| Minha conta (dados e senha) | sim | sim |
| Importação (pasta, histórico, ler novamente) | não | sim |
| Usuários (criar, editar, desativar, redefinir senha) | não | sim |

## 7. Alterando o visual (Tailwind)

O CSS compilado já está no projeto. Se você mudar classes nos templates:

```bash
npm install
npm run css          # ou: npm run css:watch
```

As cores e componentes (`.btn-primario`, `.cartao`, `.selo-ok`…) ficam em `static/src/input.css`.

## 8. Estrutura

```
config/      settings (lê o .env), urls
contas/      usuário com perfil, login, cadastro de usuários, minha conta
notas/       modelos, leitores (leitor.py, danfe.py, nfse.py), importador, monitor, telas e comandos
templates/   HTML (base, login, painel, detalhe, estatísticas, importação, usuários)
static/      CSS compilado, Chart.js, tema.js
notas_pdf/   pasta padrão das notas (com exemplos fictícios)
```

## 9. Antes de colocar em produção

Defina `DJANGO_DEBUG=0`, uma `DJANGO_SECRET_KEY` própria e `DJANGO_ALLOWED_HOSTS`; rode `python manage.py collectstatic`
e sirva os estáticos pelo servidor web (ou WhiteNoise).
