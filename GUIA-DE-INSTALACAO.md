# Refinador e Explorador — Guia de Instalação e Uso

Guia para instalar e usar os dois programas em um computador novo.
Escrito para quem não tem experiência com programação.

---

## Sumário

1. [O que são os dois programas](#1-o-que-são-os-dois-programas)
2. [O que você precisa antes de começar](#2-o-que-você-precisa-antes-de-começar)
3. [Instalando o Refinador](#3-instalando-o-refinador)
4. [Usando o Refinador](#4-usando-o-refinador)
5. [Instalando o Explorador](#5-instalando-o-explorador)
6. [Usando o Explorador](#6-usando-o-explorador)
7. [No dia a dia: abrir e fechar os programas](#7-no-dia-a-dia-abrir-e-fechar-os-programas)
8. [Problemas comuns e como resolver](#8-problemas-comuns-e-como-resolver)
9. [Limitações importantes](#9-limitações-importantes)

---

## 1. O que são os dois programas

São dois programas que trabalham em sequência, um entregando o material para o outro.

### Refinador — organiza os dados

Você exporta uma pesquisa do Qualtrics e recebe uma planilha difícil de usar:
colunas com nomes técnicos (`Q4_3`, `QID12_TEXT`), respostas em texto onde
deveria haver número, perguntas de múltipla escolha espalhadas em dezenas de
colunas separadas.

O Refinador recebe esses arquivos e devolve **uma planilha Excel limpa**, com
duas abas:

| Aba | O que tem dentro |
|---|---|
| **Data** | As respostas, uma linha por respondente, já convertidas em números e com nomes de coluna legíveis |
| **Codebook** | O dicionário: o que cada coluna significa, o texto original da pergunta, as alternativas, o tipo de variável e quais análises fazem sentido |

Ele também classifica cada pergunta por tipo (escolha única, múltipla escolha,
Likert, NPS, campo aberto, numérica, data etc.) e, se você configurar uma chave
de IA, pode sugerir nomes curtos para as variáveis e analisar o sentimento das
respostas de texto livre.

### Explorador — conversa sobre os dados

O Explorador recebe **a planilha que o Refinador gerou** e abre uma tela de
conversa. Você pergunta em português comum e ele responde com números, tabelas
e interpretação:

- "Qual é a média de satisfação geral?"
- "Existe correlação entre NPS e satisfação?"
- "Me dá o perfil demográfico da amostra."
- "Faça um resumo executivo dos dados."

Os cálculos de correlação e regressão são feitos pelo próprio programa (não pela
IA), então os números são exatos e reproduzíveis. A IA entra para interpretar e
escrever a resposta.

### A ordem importa

```
Qualtrics  →  Refinador  →  planilha .xlsx  →  Explorador  →  respostas
```

O Explorador **só aceita planilhas geradas pelo Refinador**, porque depende das
abas `Data` e `Codebook`. Uma planilha qualquer será rejeitada.

---

## 2. O que você precisa antes de começar

### 2.1 Programas de base

Instale os dois antes de qualquer outra coisa. São gratuitos e oficiais.

**Python 3.10 ou superior** — usado pelo Refinador
1. Acesse https://www.python.org/downloads/
2. Clique no botão grande de download.
3. Ao abrir o instalador, **marque a caixa "Add Python to PATH"** antes de
   clicar em Install. Essa caixa fica na primeira tela, embaixo, e é fácil de
   passar batido. Sem ela, nada funciona.
4. Conclua a instalação.

**Node.js versão 18 ou superior** — usado pelos dois programas
1. Acesse https://nodejs.org
2. Baixe a versão marcada como **LTS**.
3. Instale aceitando todas as opções padrão.

> **Como conferir se deu certo:** abra o Prompt de Comando (tecle `Windows`,
> digite `cmd`, pressione Enter) e digite `python --version` e depois
> `node --version`. Cada comando deve responder com um número de versão. Se
> aparecer "não é reconhecido como comando", a instalação não foi concluída ou a
> caixa "Add Python to PATH" não foi marcada — reinstale.

### 2.2 Se o computador não tiver direitos de administrador

Em muitas máquinas corporativas o usuário não é administrador, e aí os
instaladores comuns falham com uma mensagem de erro genérica. Os dois programas
funcionam mesmo assim — só a instalação dos pré-requisitos muda.

**Python sem administrador.** Costuma funcionar normalmente: no instalador,
escolha `Install Now` (que instala só para o seu usuário) e **não** marque
`Install for all users`. Continue marcando `Add Python to PATH`.

**Node.js sem administrador.** O instalador `.msi` do site precisa de
administrador. A alternativa é a versão portátil, que é a mesma coisa em formato
de pasta:

1. Acesse https://nodejs.org e procure a opção de download em `.zip`
   (na página de downloads, escolha Windows e o formato ZIP, versão LTS).
2. Extraia a pasta em um lugar simples, por exemplo `C:\node-portable`.
3. Avise ao Windows onde ela está:
   - Aperte `Windows`, digite `variáveis de ambiente` e escolha
     **"Editar as variáveis de ambiente para a sua conta"**.
   - Em `Variáveis de usuário`, clique na linha `Path` e depois em `Editar`.
   - Clique em `Novo`, cole o caminho da pasta (ex.: `C:\node-portable`) e
     confirme com `OK` em todas as janelas.
4. **Feche todas as janelas de comando abertas** e abra uma nova — só janelas
   novas reconhecem a mudança.
5. Confira digitando `node --version` na janela nova.

> Se nem isso for possível na sua máquina, abra um chamado para o TI pedindo a
> instalação do Node.js LTS e do Python 3.10+. São dois programas gratuitos e de
> uso comum em análise de dados.

### 2.3 Chaves de IA

Os dois programas usam inteligência artificial, mas de formas diferentes:

| Programa | Precisa de chave? | Qual chave |
|---|---|---|
| **Refinador** | Opcional | Sua própria chave da Anthropic (Claude), OpenAI (ChatGPT) ou Azure OpenAI |
| **Explorador** | Obrigatória | Chave da API de IA da Localiza (`LOCALIZA_LLM_API_KEY`) |

**O Refinador funciona sem chave nenhuma.** Ele normaliza a planilha
normalmente; você só perde dois recursos: os nomes de variáveis sugeridos por IA
e a análise de sentimento das respostas abertas.

**O Explorador não funciona sem a chave da Localiza** e sem a VPN da empresa
ativa, porque ele conversa com um serviço interno. Veja o item
[Limitações](#9-limitações-importantes).

Onde obter as chaves do Refinador, se quiser usá-las:
- Claude (Anthropic): https://console.anthropic.com
- ChatGPT (OpenAI): https://platform.openai.com/api-keys
- Azure OpenAI: Portal Azure → seu recurso OpenAI → Keys

> **Cuidado com as chaves.** Uma chave de API é como uma senha com cartão de
> crédito atrelado. Nunca mande por e-mail, nunca cole em conversa de grupo,
> nunca publique em nenhum lugar. Cada pessoa deve usar a própria chave.

### 2.4 Os arquivos dos programas

Baixe as duas pastas (`Refinador` e `Explorador`) e coloque-as em um lugar
simples do computador, por exemplo:

```
C:\Programa Refinador
C:\Programa Explorador
```

> **Use um caminho curto.** Pastas muito longas ou muito aninhadas
> (`Documentos\Trabalho\Pesquisas\2026\Ferramentas\...`) fazem a instalação
> falhar com um erro de "nome do arquivo muito grande" — é um limite do próprio
> Windows. Uma pasta direto no `C:\` é a opção mais segura.

> **Evite pastas sincronizadas** (OneDrive, Google Drive, Dropbox). A
> sincronização automática atrapalha os arquivos temporários que os programas
> criam e pode deixar tudo lento. Se você já usa uma pasta assim e está
> funcionando, pode deixar como está — mas se aparecer erro estranho ao iniciar,
> vale mover para o `C:\` ou excluir as pastas `venv` e `node_modules` da
> sincronização.

---

## 3. Instalando o Refinador

É um passo só: abra a pasta `Refinador` e dê **dois cliques em `instalar.bat`**.

Uma janela preta abre e mostra o progresso em quatro etapas:

```
[1/4] Verificando pre-requisitos...      confere Python e Node.js
[2/4] Preparando ambiente Python...      baixa as bibliotecas de dados
[3/4] Preparando a interface...          baixa as bibliotecas da tela
[4/4] Configuracao final...              cria o arquivo de configuracao
```

Leva de 2 a 5 minutos no total e mostra bastante texto passando — é normal.
Ao terminar aparece **"Instalacao concluida com sucesso!"**. Pressione qualquer
tecla para fechar a janela.

> **Não feche a janela no meio.** Se você fechar durante a etapa 2 ou 3, a
> instalação fica incompleta. Nesse caso basta rodar o `instalar.bat` de novo —
> ele detecta o que já está pronto e continua de onde parou.

### Se a instalação parar com erro

O instalador avisa exatamente qual etapa falhou. Os dois casos mais comuns:

| Mensagem | O que fazer |
|---|---|
| `ERRO: Python nao encontrado` | Instale o Python (item 2.1) marcando `Add Python to PATH` |
| `ERRO: Node.js nao encontrado` | Instale o Node.js (item 2.1), ou veja o item 2.2 se você não tiver administrador |

Em qualquer um dos dois, **feche a janela, resolva o pré-requisito e rode o
`instalar.bat` novamente.**

### Conferindo

A instalação está completa quando existirem estas duas pastas:

```
Refinador\venv\
Refinador\frontend\node_modules\
```

---

## 4. Usando o Refinador

### 4.1 Antes: exportar os dados do Qualtrics

Você precisa de **dois arquivos** da mesma pesquisa.

**Arquivo 1 — o questionário (`.qsf`)**
1. Abra a pesquisa no Qualtrics.
2. Vá em `Ferramentas` → `Importar/Exportar` → `Exportar pesquisa`.
3. Salve o arquivo. Ele termina em `.qsf`.

**Arquivo 2 — as respostas (`.xlsx`)**
1. Vá em `Dados e Análises` → `Exportar e Importar` → `Exportar dados`.
2. Escolha o formato **Excel (.xlsx)**.
3. **Marque as duas opções:**
   - "Usar valores numéricos"
   - "Dividir campos de múltipla escolha em colunas"
4. Exporte e salve.

> As duas opções do arquivo 2 são obrigatórias. Sem elas o Refinador recebe
> texto onde esperava número e o resultado sai errado.

### 4.2 Abrindo o programa

Dê **dois cliques em `iniciar.bat`**.

Vão abrir **duas janelas preta** — uma chamada "Refinador - Backend" e outra
"Refinador - Frontend". Elas precisam ficar abertas enquanto você usa o
programa. Pode minimizá-las, mas não feche.

Na janela "Refinador - Frontend" aparece um endereço, normalmente:

```
http://localhost:5173
```

Abra esse endereço no navegador (Chrome, Edge ou Firefox). Se o navegador não
abrir sozinho, copie o endereço e cole na barra do navegador.

### 4.3 Configurando a IA (opcional)

Se você tem uma chave e quer usar os recursos de IA:

1. Clique no botão de configuração, no canto superior direito da tela.
2. Escolha o provedor: Claude, ChatGPT ou Azure OpenAI.
3. Cole a chave.
4. Clique em testar a conexão para confirmar que funcionou.
5. Marque a opção de salvar se quiser que a chave continue valendo na próxima
   vez que abrir o programa.

Se você não fizer nada disso, o programa funciona sem IA.

### 4.4 As quatro etapas

A tela é um assistente que avança em quatro etapas.

**Etapa 1 — Enviar arquivos**
Arraste o `.qsf` e o `.xlsx` para as áreas indicadas. O programa lê os dois e
monta automaticamente a lista de perguntas.

**Etapa 2 — Revisar a classificação**
Aparece uma tabela com todas as colunas da pesquisa. Para cada uma, o programa
já preencheu: se entra no resultado final, o tipo da pergunta, um nome curto e o
grupo.

As linhas marcadas como **"Revisar"** são aquelas em que o programa teve menos
certeza — vale conferir essas primeiro. Você pode alterar qualquer campo:
desmarcar colunas que não interessam, corrigir um tipo, reescrever um nome.

Quando estiver satisfeita, confirme e avance.

**Etapa 3 — Respostas abertas**
Lista as perguntas de texto livre e indica quais valem uma análise de
sentimento. O programa avalia coisas como quantidade de respostas e tamanho
médio do texto para dar essa recomendação.

Marque as que você quer analisar. Se não configurou chave de IA, esta etapa não
tem efeito — apenas avance.

> **Atenção ao custo.** A análise de sentimento envia todos os comentários
> únicos daquela coluna para a IA. Em pesquisas grandes isso consome bastante da
> sua cota. Comece por uma coluna só para ter noção do custo.

**Etapa 4 — Gerar e baixar**
Clique no botão de normalizar. Ao terminar, aparece o resumo (quantas linhas,
quantas colunas) e o botão de download.

O arquivo baixado se chama `<nome-do-original>_normalized.xlsx`. **É esse
arquivo que o Explorador usa.** Guarde-o.

### 4.5 Fechando

Feche as duas janelas pretas. O programa para.

---

## 5. Instalando o Explorador

O Explorador precisa de três coisas: instalar as dependências, configurar a
chave e rodar.

### Passo 1 — Instalar as dependências

1. Abra a pasta `Explorador`.
2. Clique na barra de endereço, apague o conteúdo, digite `cmd` e pressione
   Enter.
3. Digite o primeiro comando e espere terminar:

   ```
   npm install
   ```

4. Digite o segundo comando e espere terminar:

   ```
   npm run install:all
   ```

O segundo comando é mais demorado (pode passar de 3 minutos) porque instala as
duas partes do programa. Deixe a janela aberta até o cursor voltar a piscar.

### Passo 2 — Configurar a chave da Localiza

1. Dentro da pasta `Explorador`, entre em `backend`.
2. Localize o arquivo `.env.example`.
3. Copie e cole na mesma pasta (`Ctrl+C`, `Ctrl+V`). Vai surgir algo como
   "`.env.example - Copia`".
4. Renomeie essa cópia para exatamente:

   ```
   .env
   ```

   Sim, o nome começa com ponto e não tem nada antes dele. O Windows pode
   avisar sobre mudar a extensão — confirme.
5. Abra o `.env` com o Bloco de Notas (clique com o botão direito → Abrir com →
   Bloco de Notas).
6. Substitua `cole_a_chave_aqui` pela chave real. O arquivo deve ficar assim:

   ```
   LOCALIZA_LLM_API_KEY=a_sua_chave_verdadeira_aqui
   PORT=3001
   ```

7. Salve e feche.

> Se você não conseguir ver a extensão dos arquivos, ative
> `Exibir` → `Mostrar` → `Extensões de nomes de arquivo` no Explorador de
> Arquivos. Sem isso é fácil criar `.env.txt` por acidente, e o programa não
> reconhece.

### Passo 3 — Abrir o programa

Na mesma janela preta, na pasta `Explorador`, digite:

```
npm run dev
```

A janela vai mostrar duas mensagens importantes:

```
✅ Backend rodando em http://localhost:3001
➜  Local:   http://localhost:5173
```

Abra o endereço da segunda linha no navegador.

**Essa janela precisa ficar aberta durante o uso.** Para parar o programa,
pressione `Ctrl+C` na janela ou simplesmente feche-a.

> **Se o endereço aparecer como `5174` em vez de `5173`**, é porque o Refinador
> já está usando o `5173`. Não é erro — use o endereço que apareceu na tela.

---

## 6. Usando o Explorador

1. Acesse o endereço que apareceu na janela preta.
2. Envie a planilha `_normalized.xlsx` que o Refinador gerou.
3. O programa mostra um resumo: quantos respondentes, quantas colunas, quantas
   variáveis no codebook.
4. Digite perguntas em português na caixa de conversa.

### Exemplos de perguntas que funcionam bem

**Panorama geral**
- "Me dá um resumo executivo dos dados."
- "Qual é o perfil demográfico da amostra?"
- "Quais colunas têm mais respostas em branco?"

**Números específicos**
- "Qual a média de satisfação geral?"
- "Qual é o NPS da base?"
- "Como se distribuem as respostas de faixa etária?"

**Relações entre variáveis**
- "Existe correlação entre NPS e satisfação geral?"
- "Faça uma regressão de engajamento em função de liderança."
- "Cruze satisfação com faixa etária."

**Apoio prático**
- "Crie uma fórmula de Excel para calcular a média filtrada por departamento."
- "Como você calculou esse número?"

### Como ele responde

Cada resposta vem em três blocos: uma conclusão em linguagem de negócio, uma
tabela com os números, e sugestões de próximos passos.

### O que ele evita fazer

O programa foi orientado a nunca inventar dados. Se a informação não estiver na
planilha, ele diz que não tem. Ele também avisa quando uma análise não é
estatisticamente segura — por exemplo, quando o número de respondentes daquele
corte é pequeno demais para concluir algo.

Ainda assim, **confira números que vão para uma apresentação.** A conta é feita
pelo programa, mas a leitura é feita por IA e pode interpretar mal uma pergunta
ambígua. Pedir "como você calculou isso?" mostra o passo a passo.

---

## 7. No dia a dia: abrir e fechar os programas

Depois de instalado, a rotina é curta.

### Refinador

| Ação | Como fazer |
|---|---|
| Abrir | Dois cliques em `iniciar.bat`, depois abrir `http://localhost:5173` |
| Fechar | Fechar as duas janelas pretas |

### Explorador

| Ação | Como fazer |
|---|---|
| Abrir | Abrir `cmd` na pasta, digitar `npm run dev`, abrir o endereço mostrado |
| Fechar | `Ctrl+C` na janela preta, ou fechar a janela |

### Usando os dois ao mesmo tempo

Funciona. Abra primeiro o Refinador e depois o Explorador. O segundo vai
perceber que o endereço `5173` está ocupado e usar o `5174` — o endereço correto
sempre aparece escrito na janela preta dele.

### Os endereços de cada parte

Cada programa tem duas partes: a tela (que você abre no navegador) e o motor
(que trabalha por trás). Útil se alguém pedir para você conferir se está de pé:

| Programa | Tela | Motor |
|---|---|---|
| Refinador | http://localhost:5173 | http://localhost:8000 |
| Explorador | http://localhost:5173 ou 5174 | http://localhost:3001 |

---

## 8. Problemas comuns e como resolver

### "python não é reconhecido como comando"
O Python não foi instalado ou a caixa "Add Python to PATH" não foi marcada.
Reinstale a partir de https://www.python.org/downloads/ marcando essa caixa.

### "ERRO: Ambiente virtual nao encontrado"
O `instalar.bat` não foi executado, ou foi interrompido no meio.
Rode `instalar.bat` novamente e espere a mensagem de conclusão.

### "ERRO: Dependencias do frontend nao instaladas"
A instalação da interface não foi concluída — normalmente porque a janela do
`instalar.bat` foi fechada no meio, ou porque você está com uma versão antiga do
programa. **Rode o `instalar.bat` novamente** e deixe chegar até a mensagem final.

Se preferir resolver na mão: abra `cmd` dentro da subpasta `frontend` e rode
`npm install`.

### A página fica em branco ou não carrega
A janela preta correspondente foi fechada. Os programas só funcionam com as
janelas abertas. Abra novamente.

### "LOCALIZA_LLM_API_KEY não está configurada"
O arquivo `backend\.env` não existe, está com nome errado (`.env.txt`, por
exemplo) ou a chave não foi colada. Revise o Passo 2 da instalação do
Explorador.

### "Não foi possível conectar ao serviço de IA. Verifique se a VPN da Localiza está ativa"
Exatamente o que a mensagem diz. Conecte a VPN e recarregue a página.

### "Arquivo inválido: aba 'data' não encontrada"
A planilha enviada ao Explorador não veio do Refinador. Use o arquivo que
termina em `_normalized.xlsx`.

### "Erro ao processar arquivos" no Refinador
Normalmente é a exportação do Qualtrics. Confira se o `.xlsx` foi exportado com
"Usar valores numéricos" e "Dividir campos de múltipla escolha em colunas"
marcados, e se o `.qsf` e o `.xlsx` são da **mesma** pesquisa.

### O endereço abriu em 5174 e não em 5173
Não é erro — o outro programa está usando o 5173. Use o endereço que aparece na
janela preta.

### "Sessão não encontrada ou expirada"
Você ficou muito tempo sem interagir, ou o programa foi reiniciado.
Envie a planilha novamente.

### Nada funciona e não sei por quê
Feche todas as janelas pretas, verifique se não sobrou nenhuma aberta, e comece
de novo. Se persistir, reinicie o computador — isso libera os endereços que
tenham ficado presos.

---

## 9. Limitações importantes

Leia antes de recomendar os programas para outra pessoa.

**Só rodam no próprio computador.** Não existe site na internet para acessar.
Cada pessoa instala na própria máquina e os endereços `localhost` só funcionam
ali. Ninguém acessa o seu.

**Os dados não saem do computador, com uma exceção.** As planilhas ficam na sua
máquina. O que sai são os textos enviados para a IA: no Refinador, os
comentários abertos que você mandar analisar; no Explorador, o codebook, as
estatísticas calculadas e uma amostra das primeiras linhas — enviados a cada
pergunta que você faz. Considere isso antes de usar com dados sensíveis.

**O Explorador exige rede da Localiza.** Ele depende de um serviço interno da
empresa, acessível apenas com a VPN ativa e com uma chave corporativa. Fora
desse contexto ele não funciona, e não há como contornar do lado do programa.

**O Refinador é feito para exportações do Qualtrics.** Ele lê o questionário
`.qsf` para entender as perguntas. Planilhas de outras ferramentas de pesquisa
não funcionam.

**Windows.** Os arquivos `.bat` são do Windows. Em Mac ou Linux é preciso rodar
os comandos manualmente.

**A IA cobra por uso.** No Refinador, a chave é sua e o consumo é cobrado de
você. Análise de sentimento em pesquisa grande consome bastante — comece
pequeno.

**A sessão é temporária.** O Refinador descarta os dados após 4 horas sem uso.
O Explorador perde tudo quando a janela preta é fechada. Sempre baixe e guarde
a planilha gerada.

---

*Guia referente à versão dos programas de julho de 2026.*
