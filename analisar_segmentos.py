#!/usr/bin/env python3
"""Ferramenta para validar segmentos de clientes a partir de dois arquivos CSV.

O arquivo de clientes deve conter, pelo menos, as colunas:
- Cliente
- Cliente Agrupado (opcional)
- Segmento (segmento preenchido na aba Clientes)

O arquivo de guia deve conter as colunas com os conceitos oficiais:
- Cliente Agrupado (opcional)
- Cliente (opcional)
- Segmento Recomendado

Os arquivos podem conter outras colunas, mas os nomes acima (ou variações
sem acentuação) precisam estar presentes.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def normalizar_texto(valor: Optional[str]) -> str:
    """Normaliza um texto removendo acentos e convertendo para maiúsculas."""
    if valor is None:
        return ""
    valor = valor.strip()
    if not valor:
        return ""
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(ch for ch in valor if not unicodedata.combining(ch))
    return valor.upper()


def slug_coluna(nome: str) -> str:
    """Cria um identificador simplificado para o nome de uma coluna."""
    nome_normalizado = normalizar_texto(nome)
    return nome_normalizado.replace(" ", "_")


def identificar_coluna(cabecalho: Sequence[str], alternativas: Sequence[str], obrigatoria: bool = True) -> Optional[str]:
    """Encontra o nome da coluna considerando aliases em português."""
    colunas_norm = {slug_coluna(coluna): coluna for coluna in cabecalho}
    for alias in alternativas:
        alias_slug = slug_coluna(alias)
        if alias_slug in colunas_norm:
            return colunas_norm[alias_slug]
    if obrigatoria:
        raise ValueError(
            f"Não foi possível localizar nenhuma das colunas {alternativas}.")
    return None


def ler_csv(caminho: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    try:
        with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            if leitor.fieldnames is None:
                raise ValueError("Arquivo CSV sem cabeçalho válido.")
            cabecalho = [campo.strip() for campo in leitor.fieldnames]
            linhas = []
            for linha in leitor:
                linha_limpa = {campo.strip(): (valor.strip() if valor is not None else "")
                               for campo, valor in linha.items()}
                linhas.append(linha_limpa)
            return linhas, cabecalho
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}") from None


def montar_mapa_segmentos(registros: Iterable[Dict[str, str]], coluna_chave: Optional[str], coluna_segmento: str) -> Dict[str, set]:
    mapa: Dict[str, set] = defaultdict(set)
    if coluna_chave is None:
        return mapa
    for registro in registros:
        chave = normalizar_texto(registro.get(coluna_chave, ""))
        segmento = normalizar_texto(registro.get(coluna_segmento, ""))
        if chave and segmento:
            mapa[chave].add(segmento)
    return mapa


def extrair_segmento_unico(mapa: Dict[str, set]) -> Tuple[Dict[str, str], Dict[str, set]]:
    unicos: Dict[str, str] = {}
    conflitos: Dict[str, set] = {}
    for chave, segmentos in mapa.items():
        if len(segmentos) == 1:
            unicos[chave] = next(iter(segmentos))
        elif segmentos:
            conflitos[chave] = segmentos
    return unicos, conflitos


def formatar_tabela(linhas: Sequence[Dict[str, str]], colunas: Sequence[str]) -> str:
    if not linhas:
        return "(nenhum registro)"
    larguras = [len(coluna) for coluna in colunas]
    for linha in linhas:
        for indice, coluna in enumerate(colunas):
            larguras[indice] = max(larguras[indice], len(linha.get(coluna, "")))

    def formatar_linha(valores: Sequence[str]) -> str:
        return " | ".join(valor.ljust(larguras[i]) for i, valor in enumerate(valores))

    linhas_formatadas = [formatar_linha(colunas)]
    linhas_formatadas.append("-+-".join("-" * largura for largura in larguras))
    for linha in linhas:
        valores = [linha.get(coluna, "") for coluna in colunas]
        linhas_formatadas.append(formatar_linha(valores))
    return "\n".join(linhas_formatadas)


def gerar_relatorio(caminho_clientes: Path, caminho_guia: Path, exportar: Optional[Path] = None) -> None:
    clientes, cabecalho_clientes = ler_csv(caminho_clientes)
    guia, cabecalho_guia = ler_csv(caminho_guia)

    col_cliente = identificar_coluna(cabecalho_clientes, ["Cliente", "Nome do Cliente", "Razao Social"])
    col_agrupado = identificar_coluna(cabecalho_clientes, ["Cliente Agrupado", "Agrupamento", "Grupo"], obrigatoria=False)
    col_segmento = identificar_coluna(cabecalho_clientes, ["Segmento", "Segmento Atual", "Segmentacao"])

    col_guia_agrupado = identificar_coluna(cabecalho_guia, ["Cliente Agrupado", "Agrupamento", "Grupo"], obrigatoria=False)
    col_guia_cliente = identificar_coluna(cabecalho_guia, ["Cliente", "Nome do Cliente", "Razao Social"], obrigatoria=False)
    col_guia_segmento = identificar_coluna(cabecalho_guia, ["Segmento Recomendado", "Segmento", "Segmento Oficial"])

    mapa_guia_agrupado = montar_mapa_segmentos(guia, col_guia_agrupado, col_guia_segmento)
    mapa_guia_cliente = montar_mapa_segmentos(guia, col_guia_cliente, col_guia_segmento)

    segmentos_por_agrupado, conflitos_guia_agrupado = extrair_segmento_unico(mapa_guia_agrupado)
    segmentos_por_cliente, conflitos_guia_cliente = extrair_segmento_unico(mapa_guia_cliente)

    resultados: List[Dict[str, str]] = []
    segmentos_por_agrupado_planilha: Dict[str, set] = defaultdict(set)

    for registro in clientes:
        cliente_nome = registro.get(col_cliente, "")
        agrupado_nome = registro.get(col_agrupado, "") if col_agrupado else ""
        segmento_preenchido = registro.get(col_segmento, "")

        cliente_norm = normalizar_texto(cliente_nome)
        agrupado_norm = normalizar_texto(agrupado_nome)
        segmento_norm = normalizar_texto(segmento_preenchido)

        if agrupado_norm:
            segmentos_por_agrupado_planilha[agrupado_norm].add(segmento_norm)

        status = ""
        observacao = ""
        segmento_recomendado = ""

        if agrupado_norm and agrupado_norm in conflitos_guia_agrupado:
            status = "Conflito na Guia (Cliente Agrupado)"
            observacao = ", ".join(sorted(conflitos_guia_agrupado[agrupado_norm]))
        elif cliente_norm and cliente_norm in conflitos_guia_cliente:
            status = "Conflito na Guia (Cliente)"
            observacao = ", ".join(sorted(conflitos_guia_cliente[cliente_norm]))
        else:
            if agrupado_norm and agrupado_norm in segmentos_por_agrupado:
                segmento_recomendado = segmentos_por_agrupado[agrupado_norm]
            elif cliente_norm and cliente_norm in segmentos_por_cliente:
                segmento_recomendado = segmentos_por_cliente[cliente_norm]

            if not segmento_recomendado:
                status = "Sem mapeamento na Guia"
            else:
                if segmento_norm == segmento_recomendado:
                    status = "Segmento correto"
                else:
                    status = "Divergente"
                    observacao = segmento_recomendado

        resultados.append({
            "Cliente": cliente_nome,
            "Cliente Agrupado": agrupado_nome,
            "Segmento informado": segmento_preenchido,
            "Segmento recomendado": segmento_recomendado,
            "Status": status,
            "Observação": observacao,
        })

    contagem_status = Counter(resultado["Status"] for resultado in resultados)

    print("Resumo geral")
    print("============")
    total_registros = len(resultados)
    for status, quantidade in contagem_status.most_common():
        percentual = (quantidade / total_registros * 100) if total_registros else 0
        print(f"- {status}: {quantidade} registro(s) ({percentual:.1f}%)")
    print(f"- Total analisado: {total_registros}\n")

    divergentes = [r for r in resultados if r["Status"] == "Divergente"]
    if divergentes:
        print("Casos divergentes (segmento diferente do recomendado)")
        print("----------------------------------------------------")
        print(formatar_tabela(divergentes,
                              ["Cliente", "Cliente Agrupado", "Segmento informado", "Segmento recomendado"]))
        print()

    sem_mapeamento = [r for r in resultados if r["Status"] == "Sem mapeamento na Guia"]
    if sem_mapeamento:
        print("Clientes sem mapeamento na Guia")
        print("--------------------------------")
        print(formatar_tabela(sem_mapeamento,
                              ["Cliente", "Cliente Agrupado", "Segmento informado"]))
        print()

    conflitos_guia = [r for r in resultados if r["Status"].startswith("Conflito na Guia")]
    if conflitos_guia:
        print("Conflitos encontrados na Guia")
        print("------------------------------")
        print(formatar_tabela(conflitos_guia,
                              ["Cliente", "Cliente Agrupado", "Status", "Observação"]))
        print()

    conflitos_planilha = []
    for agrupado_norm, segmentos in sorted(segmentos_por_agrupado_planilha.items()):
        if len(segmentos) > 1:
            # Procurar o nome original do agrupamento (primeira ocorrência)
            nome_original = ""
            for registro in clientes:
                if normalizar_texto(registro.get(col_agrupado, "")) == agrupado_norm:
                    nome_original = registro.get(col_agrupado, "")
                    break
            conflitos_planilha.append({
                "Cliente Agrupado": nome_original,
                "Segmentos encontrados": ", ".join(sorted(segmentos)),
            })

    if conflitos_planilha:
        print("Cliente Agrupado com múltiplos segmentos na aba Clientes")
        print("--------------------------------------------------------")
        print(formatar_tabela(conflitos_planilha,
                              ["Cliente Agrupado", "Segmentos encontrados"]))
        print()

    if exportar:
        caminho_exportar = exportar.with_suffix(exportar.suffix or ".csv")
        with caminho_exportar.open("w", encoding="utf-8", newline="") as arquivo:
            campos = ["Cliente", "Cliente Agrupado", "Segmento informado", "Segmento recomendado", "Status", "Observação"]
            escritor = csv.DictWriter(arquivo, fieldnames=campos)
            escritor.writeheader()
            for linha in resultados:
                escritor.writerow(linha)
        print(f"Relatório salvo em: {caminho_exportar}")


def criar_argumentos(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara o segmento informado na aba Clientes com o segmento recomendado na aba Guia.")
    parser.add_argument("--clientes", required=True, type=Path,
                        help="Caminho para o arquivo CSV da aba Clientes")
    parser.add_argument("--guia", required=True, type=Path,
                        help="Caminho para o arquivo CSV da aba Guia")
    parser.add_argument("--exportar", type=Path,
                        help="Opcional: caminho para exportar o relatório consolidado em CSV")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = criar_argumentos(argv)
        gerar_relatorio(args.clientes, args.guia, args.exportar)
        return 0
    except Exception as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
