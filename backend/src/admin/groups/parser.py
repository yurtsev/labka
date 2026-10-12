import csv
import io
import re


class InviteListParser:
    """Разбор списка почт: из текста (по строкам, через запятую, точку с запятой или пробел)
    или из CSV (почта — в первом столбце). Проверка почт — в сервисе."""

    @staticmethod
    def from_text(text: str) -> list[str]:
        return [item for item in re.split(r"[\s,;]+", text) if item]

    @staticmethod
    def from_csv(content: bytes) -> list[str]:
        """Первый столбец каждой непустой строки; заголовок `email` или `почта` пропускается."""
        decoded = content.decode("utf-8-sig", errors="replace")
        rows = [
            row
            for row in csv.reader(
                io.StringIO(decoded), delimiter=InviteListParser._delimiter(decoded)
            )
            if row
        ]
        cells = [row[0].strip() for row in rows if row[0].strip()]
        if cells and cells[0].lower() in {"email", "e-mail", "mail", "почта", "email студента"}:
            cells = cells[1:]
        return cells

    @staticmethod
    def _delimiter(decoded: str) -> str:
        first_line = decoded.splitlines()[0] if decoded.strip() else ""
        return ";" if first_line.count(";") > first_line.count(",") else ","
