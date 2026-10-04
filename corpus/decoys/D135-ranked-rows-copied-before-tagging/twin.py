"""순위 매기기 - 행마다 사본을 만든 뒤 그 사본에 순위를 적는다."""


def rank(rows: list[dict[str, int]]) -> list[dict[str, int]]:
    ranked = list(rows)
    if any(isinstance(row.get("score"), bool) for row in ranked):
        raise TypeError("score 는 bool 이 아닌 정수다")
    ranked.sort(key=lambda row: row["score"], reverse=True)
    for place, row in enumerate(ranked, 1):
        row["rank"] = place
    return ranked
