# Refinador

Transforma exports do Qualtrics em planilhas normalizadas prontas para analise.

## Pre-requisitos

- Python 3.10 ou superior instalado.
  - Baixe em: https://www.python.org/downloads/
  - Durante a instalacao, marque `Add Python to PATH`.
- Node.js 18 ou superior instalado.
  - Baixe a versao LTS em: https://nodejs.org

## Instalacao

1. Execute `instalar.bat` e aguarde a conclusao (instala as dependencias Python).
2. Abra um terminal na subpasta `frontend` e execute `npm install`
   (instala as dependencias da interface).

O passo 2 e obrigatorio e ainda nao esta automatizado no `instalar.bat`. Sem ele,
o `iniciar.bat` falha com a mensagem "Dependencias do frontend nao instaladas".

Para um passo a passo detalhado, voltado a quem nao tem experiencia tecnica,
veja [GUIA-DE-INSTALACAO.md](GUIA-DE-INSTALACAO.md).

## Como usar

1. Execute `iniciar.bat`.
2. O aplicativo abre no navegador.
3. Envie o questionario `.qsf` e os dados numericos `.xlsx`, ambos exportados do Qualtrics.
4. Revise a configuracao das colunas.
5. Clique em `Normalizar` e baixe o arquivo final.

## Configuracao da IA

Para nomes de variaveis por IA e analise de sentimento:

1. Clique no botao de configuracao no canto superior direito do app.
2. Escolha o provedor: Claude, ChatGPT ou Azure OpenAI.
3. Cole sua chave de API.
4. Marque a opcao para salvar na proxima sessao se quiser persistir.

### Onde obter a chave

- Claude (Anthropic): https://console.anthropic.com
- ChatGPT (OpenAI): https://platform.openai.com/api-keys
- Azure OpenAI: Portal Azure > recurso OpenAI > Keys

## Como exportar do Qualtrics

### Questionario (.qsf)

1. Abra a pesquisa no Qualtrics.
2. Clique em `Ferramentas > Importar/Exportar > Exportar pesquisa`.
3. Salve o arquivo `.qsf`.

### Dados numericos (.xlsx)

1. Va em `Dados e Analises > Exportar e Importar > Exportar dados`.
2. Escolha o formato `Excel (.xlsx)`.
3. Marque `Usar valores numericos` e `Dividir campos de multipla escolha em colunas`.
4. Exporte e salve o arquivo.

## Encerramento

Feche a janela do terminal aberta junto com o aplicativo para encerrar a execucao.
