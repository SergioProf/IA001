from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook


BASE_DIR = Path(__file__).resolve().parent
# Todos os arquivos ficam na mesma pasta deste script.
SOURCE_FILE = BASE_DIR / "MapaSalas.xlsx"
OUTPUT_FILE = BASE_DIR / "mapa_salas_tidy.csv"
REPORT_FILE = BASE_DIR / "relatorio_transformacao_mapa_salas.md"

# Textos usados para reconhecer as colunas de dias na grade semanal.
WEEKDAYS = ("SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "DOMINGO")


def normalize_text(value: Any) -> str:
    """Converte valores em texto e remove espaços redundantes para comparação."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_key(value: Any) -> str:
    """Padroniza a chave CODIGO-TURMA usada para juntar grade e descrição."""
    return normalize_text(value).upper().replace(" - ", "-").replace(" -", "-").replace("- ", "-")


def find_labeled_cell(rows: list[tuple[Any, ...]], label: str) -> tuple[int, int, str] | None:
    """Localiza uma célula cujo conteúdo começa com o rótulo informado."""
    expected = label.upper()
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            text = normalize_text(value)
            if text.upper().startswith(expected):
                return row_index, column_index, text
    return None


def value_after_label(text: str) -> str:
    """Extrai o valor após ':' em campos como 'Sala: Sala 103'."""
    return normalize_text(text.split(":", maxsplit=1)[-1])


def labeled_value(rows: list[tuple[Any, ...]], label: str) -> str:
    """Lê o valor do rótulo, seja na própria célula ou na célula seguinte."""
    labeled_cell = find_labeled_cell(rows, label)
    if not labeled_cell:
        return ""
    row_index, column_index, text = labeled_cell
    value = value_after_label(text)
    return value if value.upper() != label.rstrip(":").upper() else normalize_text(cell_value(rows[row_index], column_index + 1))


def cell_value(row: tuple[Any, ...], column: int) -> Any:
    """Lê uma célula com segurança em linhas vazias ou encurtadas do Excel."""
    return row[column] if column < len(row) else None


def parse_class_identifier(value: Any) -> tuple[str, list[str]] | None:
    """Separa 'ARQ01045-A/B' em código 'ARQ01045' e turmas ['A', 'B']."""
    match = re.match(r"^([A-Z0-9]+)\s*-\s*([A-Z0-9]+(?:\s*/\s*[A-Z0-9]+)*)$", normalize_key(value))
    if not match:
        return None
    return match.group(1), [part.strip() for part in match.group(2).split("/")]


def format_time(value: Any) -> str:
    """Padroniza horários vindos do Excel no formato HH:MM."""
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    text = normalize_text(value)
    match = re.search(r"(\d{1,2})[:h](\d{2})", text)
    if not match:
        raise ValueError(f"Horario nao reconhecido: {value!r}")
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def end_time(start: str, periods: int) -> str:
    """Calcula o fim de um encontro sabendo seu início e total de períodos."""
    start_datetime = datetime.strptime(start, "%H:%M")
    return (start_datetime + timedelta(hours=periods)).strftime("%H:%M")


def split_courses(value: Any) -> list[str]:
    """Separa cursos registrados juntos, por exemplo 'DVIS/DPRO'."""
    courses = [course.strip() for course in re.split(r"\s*[/;,]\s*", normalize_text(value)) if course.strip()]
    return courses or [""]


def allocate_vacancies(total: Any, class_names: list[str]) -> dict[str, int | None]:
    """Divide vagas compartilhadas; a primeira turma recebe eventual resto."""
    if pd.isna(total):
        return {class_name: None for class_name in class_names}
    total_int = int(float(total))
    base, remainder = divmod(total_int, len(class_names))
    return {class_name: base + int(index < remainder) for index, class_name in enumerate(class_names)}


def extract_metadata(rows: list[tuple[Any, ...]]) -> tuple[str, str, str, str, str]:
    """Lê os metadados físicos e acadêmicos do cabeçalho de uma aba."""
    semester = labeled_value(rows, "PERÍODO LETIVO:")
    room = labeled_value(rows, "SALA:")
    if not semester or not room:
        raise ValueError("Cabecalho sem 'Sala:' ou 'Periodo Letivo:'")
    return (
        semester,
        labeled_value(rows, "PRÉDIO:"),
        room,
        labeled_value(rows, "TIPO DE SALA"),
        labeled_value(rows, "CAPACIDADE"),
    )


def extract_descriptions(rows: list[tuple[Any, ...]]) -> dict[str, dict[str, Any]]:
    """Lê a tabela inferior e cria um dicionário indexado por Sigla Turma."""
    header_row = next(
        (
            index
            for index, row in enumerate(rows)
            if any(normalize_text(cell).upper() == "SIGLA TURMA" for cell in row)
        ),
        None,
    )
    if header_row is None:
        raise ValueError("Tabela descritiva sem cabecalho 'Sigla Turma'")

    headers = {normalize_text(value).upper(): index for index, value in enumerate(rows[header_row])}
    required = ("SIGLA TURMA", "ATIVIDADE", "CURSOS", "VAGAS OFERECIDAS")
    missing = [header for header in required if header not in headers]
    if missing:
        raise ValueError(f"Tabela descritiva sem colunas: {', '.join(missing)}")

    # A chave permite buscar rapidamente os atributos ao ler a grade semanal.
    descriptions: dict[str, dict[str, Any]] = {}
    for row in rows[header_row + 1 :]:
        identifier = normalize_key(cell_value(row, headers["SIGLA TURMA"]))
        if not identifier:
            continue
        parsed = parse_class_identifier(identifier)
        if not parsed:
            continue
        descriptions[identifier] = {
            "nome_disciplina": normalize_text(cell_value(row, headers["ATIVIDADE"])),
            "cursos": split_courses(cell_value(row, headers["CURSOS"])),
            "vagas_totais_compartilhadas": cell_value(row, headers["VAGAS OFERECIDAS"]),
        }
    return descriptions


def extract_schedule(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """Converte células preenchidas da grade em registros de turma-dia-período."""
    hour_header = find_labeled_cell(rows, "HORA")
    if not hour_header:
        raise ValueError("Grade semanal sem cabecalho 'Hora'")
    header_row, hour_column, _ = hour_header
    # Mapeia o índice de cada coluna ao respectivo dia da semana.
    day_columns = {
        column: normalize_text(value).upper()
        for column, value in enumerate(rows[header_row])
        if any(day in normalize_text(value).upper() for day in WEEKDAYS)
    }
    if not day_columns:
        raise ValueError("Grade semanal sem colunas de dias")

    records: list[dict[str, Any]] = []
    for row in rows[header_row + 1 :]:
        if not normalize_text(cell_value(row, hour_column)):
            continue
        try:
            period_start = format_time(cell_value(row, hour_column))
        except ValueError:
            continue
        for column, weekday in day_columns.items():
            parsed = parse_class_identifier(cell_value(row, column))
            if not parsed:
                continue
            code, class_names = parsed
            raw_identifier = normalize_key(cell_value(row, column))
            # A/B representa duas turmas simultâneas e gera um registro para cada uma.
            for class_name in class_names:
                records.append(
                    {
                        "identificador_original": raw_identifier,
                        "codigo_disciplina": code,
                        "turma": class_name,
                        "dia_semana": weekday,
                        "hora_inicio": period_start,
                    }
                )
    return records


def consolidate_periods(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Une períodos consecutivos da mesma turma, sala e dia em um encontro."""
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(record["sala"], record["codigo_disciplina"], record["turma"], record["dia_semana"])].append(record)

    consolidated: list[dict[str, Any]] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: item["hora_inicio"])
        block = [ordered[0]]
        for record in ordered[1:]:
            # Horários adjacentes pertencem ao mesmo encontro.
            previous_end = end_time(block[-1]["hora_inicio"], 1)
            if record["hora_inicio"] == previous_end:
                block.append(record)
            else:
                consolidated.append(make_consolidated_record(block))
                block = [record]
        consolidated.append(make_consolidated_record(block))
    return consolidated


def make_consolidated_record(block: list[dict[str, Any]]) -> dict[str, Any]:
    """Produz o registro final de uma sequência contínua de períodos."""
    record = block[0].copy()
    record["numero_periodos"] = len(block)
    record["hora_fim"] = end_time(record["hora_inicio"], len(block))
    return record


def transform_workbook() -> tuple[pd.DataFrame, list[str], list[str]]:
    """Processa todas as salas e devolve o DataFrame Tidy e ocorrências pendentes."""
    workbook = load_workbook(SOURCE_FILE, data_only=True, read_only=True)
    all_records: list[dict[str, Any]] = []
    missing_descriptions: list[str] = []
    processed_sheets: list[str] = []

    for sheet_name in workbook.sheetnames:
        # Cada aba descreve uma sala e contém cabeçalho, grade e tabela inferior.
        worksheet = workbook[sheet_name]
        rows = list(worksheet.iter_rows(values_only=True))
        semester, building, room, room_type, class_capacity = extract_metadata(rows)
        descriptions = extract_descriptions(rows)
        schedule = extract_schedule(rows)
        processed_sheets.append(sheet_name)

        for record in schedule:
            # Junta a ocupação da grade aos dados descritivos da turma.
            description = descriptions.get(record["identificador_original"])
            if description is None:
                missing_descriptions.append(f"{sheet_name}: {record['identificador_original']}")
                continue
            parsed = parse_class_identifier(record["identificador_original"])
            assert parsed is not None
            _, class_names = parsed
            vacancies = allocate_vacancies(description["vagas_totais_compartilhadas"], class_names)
            record.update(
                {
                    "semestre": semester,
                    "predio": building,
                    "sala": room,
                    "tipo_sala": room_type,
                    "capacidade_turma": class_capacity,
                    "nome_disciplina": description["nome_disciplina"],
                    "cursos": description["cursos"],
                    "vagas_oferecidas": vacancies[record["turma"]],
                    "vagas_totais_compartilhadas": description["vagas_totais_compartilhadas"],
                    "turmas_compartilhando_sala": "/".join(class_names),
                }
            )
            all_records.append(record)

    # A grade tem um registro por período; a saída deve ter um registro por encontro.
    consolidated = consolidate_periods(all_records)
    output_records = []
    for record in consolidated:
        # Uma disciplina que atende vários cursos permanece em um CSV, uma linha por curso.
        for course in record.pop("cursos"):
            output_records.append({**record, "curso": course})

    columns = [
        "semestre", "predio", "sala", "tipo_sala", "capacidade_turma", "codigo_disciplina", "turma", "nome_disciplina", "curso",
        "dia_semana", "hora_inicio", "hora_fim", "numero_periodos", "vagas_oferecidas",
        "vagas_totais_compartilhadas", "turmas_compartilhando_sala",
    ]
    return pd.DataFrame(output_records, columns=columns), processed_sheets, sorted(set(missing_descriptions))


def write_report(data: pd.DataFrame, sheets: list[str], missing_descriptions: list[str]) -> None:
    """Gera um resumo para auditar a transformação e identificar exceções."""
    report = [
        "# Relatorio da Transformacao - Mapa de Salas",
        "",
        f"- Arquivo de origem: `{SOURCE_FILE.name}`",
        f"- Abas processadas: {len(sheets)}",
        f"- Registros Tidy: {len(data)}",
        f"- Colunas: {len(data.columns)}",
        f"- Registros duplicados: {int(data.duplicated().sum())}",
        "",
        "## Valores ausentes",
        "",
    ]
    report.extend(f"- `{column}`: {int(count)}" for column, count in data.isna().sum().items())
    report.extend(["", "## Chaves da grade sem descricao", ""])
    report.extend(f"- {item}" for item in missing_descriptions) if missing_descriptions else report.append("- Nenhuma")
    report.extend(["", "## Regras aplicadas", "", "- Turmas separadas por `/` receberam registros independentes.", "- Vagas compartilhadas foram divididas entre as turmas; a primeira recebeu eventual resto.", "- Periodos consecutivos foram consolidados em um encontro.", "- Cursos separados por `/`, `;` ou `,` foram desagregados em linhas."])
    REPORT_FILE.write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    """Executa a transformação, grava os arquivos de saída e mostra uma amostra."""
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Arquivo de origem nao encontrado: {SOURCE_FILE}")
    data, sheets, missing_descriptions = transform_workbook()
    if data.empty:
        raise ValueError("Nenhum encontro foi extraido do arquivo de origem.")
    # utf-8-sig mantém acentos corretos quando o CSV é aberto diretamente no Excel.
    data.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    write_report(data, sheets, missing_descriptions)
    print(f"CSV criado: {OUTPUT_FILE.name} ({len(data)} registros, {len(data.columns)} colunas)")
    print(f"Relatorio criado: {REPORT_FILE.name}")
    print(data.head().to_string(index=False))


if __name__ == "__main__":
    main()