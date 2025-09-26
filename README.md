# Ferramenta de revisão de segmentos de clientes

Este repositório agora contém um script em Python capaz de comparar os segmentos
preenchidos na aba **Clientes** de uma planilha com o conceito oficial descrito
na aba **Guia**. A ferramenta gera um relatório consolidado que aponta:

- clientes com segmento divergente do recomendado;
- cadastros sem mapeamento na aba Guia;
- conflitos existentes na própria aba Guia (quando o mesmo cliente aparece com
  mais de um segmento oficial);
- agrupamentos que aparecem com múltiplos segmentos diferentes na aba Clientes.

O objetivo é permitir uma análise robusta e reproduzível, já executada aqui com
um conjunto de dados de exemplo.

## Preparando os dados

1. Exporte a aba **Clientes** da planilha para CSV (UTF-8). O arquivo deve conter
   pelo menos as colunas:
   - `Cliente`
   - `Segmento`
   - `Cliente Agrupado` (opcional, mas recomendado)
2. Exporte a aba **Guia** para CSV (UTF-8). São utilizados os campos:
   - `Segmento Recomendado` (ou `Segmento` / `Segmento Oficial`)
   - `Cliente Agrupado` (opcional)
   - `Cliente` (opcional)

Os nomes das colunas podem variar levemente (ex.: "Razao Social" ou "Segmento
Atual"); o script reconhece essas variações automaticamente.

## Como executar

```bash
python analisar_segmentos.py --clientes CAMINHO_CLIENTES.csv \
                             --guia CAMINHO_GUIA.csv \
                             --exportar relatorio.csv
```

- O parâmetro `--exportar` é opcional e gera um CSV consolidado com todas as
  colunas de resultado.
- A saída no terminal já mostra um resumo geral, além de tabelas com as
  inconsistências encontradas.

## Status possíveis

- **Segmento correto** – o segmento informado na aba Clientes coincide com o
  recomendado pela Guia.
- **Divergente** – o segmento informado é diferente do recomendado. A coluna
  "Observação" aponta o segmento esperado.
- **Sem mapeamento na Guia** – não há correspondência para o cliente nem para o
  agrupamento na aba Guia.
- **Conflito na Guia** – o mesmo cliente (ou cliente agrupado) aparece com mais
  de um segmento oficial na aba Guia, impedindo a recomendação automática.

## Execução em dados de exemplo

Arquivos disponíveis em `dados_exemplo/` foram usados para validar o script.
O comando abaixo já foi executado no ambiente e gerou o relatório demonstrado na
sequência:

```bash
python analisar_segmentos.py \
  --clientes dados_exemplo/clientes_exemplo.csv \
  --guia dados_exemplo/guia_exemplo.csv \
  --exportar dados_exemplo/relatorio_exemplo.csv
```

Trecho da saída obtida:

```
Resumo geral
============
- Segmento correto: 8 registro(s) (72.7%)
- Divergente: 3 registro(s) (27.3%)
- Total analisado: 11
```

As tabelas impressas em seguida apresentam os clientes divergentes e os
agrupamentos que possuem mais de um segmento informado. O arquivo
`dados_exemplo/relatorio_exemplo.csv` contém todas as colunas consolidadas para
auditoria posterior.
