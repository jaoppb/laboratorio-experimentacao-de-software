import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class CSVManager:
    """Gerenciador de arquivos CSV para dados do Lab02.

    Mantém o padrão estabelecido no Lab01, adicionando suporte a gravações
    incrementais (append) atômicas por trial sem sobrescrever dados anteriores.
    """

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, rows: List[Dict[str, Any]], filename: str) -> Path:
        """Salva uma lista de registros sobrescrevendo o arquivo existente (padrão Lab01)."""
        if not rows:
            logger.warning("no_rows_to_save", filename=filename)
            return self.output_dir / filename

        filepath = self.output_dir / filename

        # Coleta todas as chaves únicas preservando a ordem do primeiro registro
        fieldnames: List[str] = []
        for row in rows:
            for k in row.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("saved_records", count=len(rows), destination=str(filepath))
        return filepath

    def append_record(
        self,
        record: Dict[str, Any],
        filename: str,
        fieldnames: Optional[List[str]] = None,
    ) -> Path:
        """Adiciona um único registro ao final do CSV.

        Se o arquivo não existir ou estiver vazio, escreve o cabeçalho primeiro.
        """
        filepath = self.output_dir / filename
        file_exists = filepath.exists() and filepath.stat().st_size > 0

        # Determina os nomes dos campos
        if fieldnames is None:
            if file_exists:
                # Lê os cabeçalhos existentes
                with open(filepath, "r", newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    try:
                        fieldnames = next(reader)
                    except StopIteration:
                        fieldnames = list(record.keys())
            else:
                fieldnames = list(record.keys())

        # Garante que chaves extras sejam acomodadas
        for k in record.keys():
            if k not in fieldnames:
                fieldnames.append(k)

        # Se o arquivo não existia, escreve com header
        if not file_exists:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(record)
        else:
            with open(filepath, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(record)

        logger.info("appended_record", trial=record.get("trial_id", ""), destination=str(filepath))
        return filepath

    def read_records(self, filename: str) -> List[Dict[str, str]]:
        """Lê todos os registros de um arquivo CSV existente."""
        filepath = self.output_dir / filename
        if not filepath.exists():
            return []

        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def merge_and_save(
        self, datasets: List[List[Dict[str, Any]]], filename: str, merge_key: str = "trial_id"
    ) -> Path:
        """Funde múltiplos datasets com base em uma chave comum (padrão Lab01)."""
        if not datasets:
            logger.warning("no_datasets_to_merge", filename=filename)
            return self.output_dir / filename

        merged_data: Dict[Any, Dict[str, Any]] = {}
        for dataset in datasets:
            for row in dataset:
                key = row.get(merge_key)
                if key:
                    if key not in merged_data:
                        merged_data[key] = {}
                    merged_data[key].update(row)

        final_rows = list(merged_data.values())
        return self.save(final_rows, filename)
