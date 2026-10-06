import os
from typing import Optional, List

import psycopg2
import pdfplumber
from pydantic import BaseModel
from pypdf import PdfReader
from langchain_tavily import TavilySearch
from src.prompts import ENRICHMENT_SYSTEM_PROMPT, REPORT_SYSTEM_PROMPT


# ── 도구: 웹 검색 ──
search_tool = TavilySearch(max_results=3)


# ── 도구: PDF 텍스트 추출 ──
def extract_text_from_pdf(file_path: str) -> str:
    """PDF 파일에서 텍스트를 추출한다.
    pypdf로 먼저 시도하고, 실패하거나 텍스트가 비어있으면 pdfplumber로 재시도한다."""
    text = ""
    try:
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        text = ""

    if not text.strip():
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    return text


# ── 도구: 텍스트 파일 읽기 ──
def extract_text_from_txt(file_path: str) -> str:
    """텍스트 파일을 그대로 읽는다."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# ── 구조화된 출력 스키마 ──
class ProductInfo(BaseModel):
    product_name: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None


class IngredientInfo(BaseModel):
    original_name: str
    ratio: Optional[float] = None
    eu_name: Optional[str] = None
    e_number: Optional[str] = None
    allergen_category: Optional[str] = None


class ExtractionResult(BaseModel):
    product: ProductInfo
    ingredients: List[IngredientInfo]


# ── DB 연결 ──
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


# ── DB 저장: 제품 정보 ──
def save_product(product: ProductInfo) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO product (product_name, category, manufacturer)
        VALUES (%s, %s, %s)
        RETURNING product_id;
        """,
        (product.product_name, product.category, product.manufacturer),
    )
    product_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return product_id


# ── DB 저장: 성분 + 정규화 + 제품-성분 연결 ──
def save_ingredients(product_id: int, ingredients: List[IngredientInfo]) -> List[int]:
    conn = get_connection()
    cursor = conn.cursor()
    ingredient_ids = []

    for order, item in enumerate(ingredients, start=1):
        cursor.execute(
            """
            INSERT INTO ingredient (ingredient_name)
            VALUES (%s)
            RETURNING ingredient_id;
            """,
            (item.original_name,),
        )
        ingredient_id = cursor.fetchone()[0]
        ingredient_ids.append(ingredient_id)

        cursor.execute(
            """
            INSERT INTO ingredient_normalization
                (ingredient_id, original_name, eu_name, e_number, allergen_category)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (
                ingredient_id,
                item.original_name,
                item.eu_name,
                item.e_number,
                item.allergen_category,
            ),
        )

        cursor.execute(
            """
            INSERT INTO product_ingredient
                (product_id, ingredient_id, ingredient_order, ratio)
            VALUES (%s, %s, %s, %s);
            """,
            (product_id, ingredient_id, order, item.ratio),
        )

    conn.commit()
    cursor.close()
    conn.close()
    return ingredient_ids


from langchain_openai import ChatOpenAI


class EnrichmentInfo(BaseModel):
    eu_name: Optional[str] = None
    e_number: Optional[str] = None


_enrichment_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def enrich_ingredient(name: str) -> EnrichmentInfo:
    """성분 하나를 독립적으로 검색하고, EU 표준명/E-number를 판단한다.
    매번 새로운 대화로 시작하므로 맥락이 누적되지 않는다."""
    from src.prompts import ENRICHMENT_SYSTEM_PROMPT

    search_results = search_tool.invoke(
        f"{name} food additive E number EU standard name"
    )

    structured_model = _enrichment_model.with_structured_output(EnrichmentInfo)
    return structured_model.invoke([
        {"role": "system", "content": ENRICHMENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Ingredient: {name}\n\nSearch results: {search_results}"},
    ])

class ExportReport(BaseModel):
    is_exportable: bool
    summary: str
    violations: list[str]
    recommendations: list[str]


def generate_export_report(compliance_results: list[dict]) -> ExportReport:
    """성분별 규정 준수 결과를 종합해서 최종 수출 가능 여부 리포트 생성 (격리된 호출)"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(ExportReport)

    results_text = "\n".join(
        f"- {r['ingredient_name']} ({r['e_number'] or 'N/A'}): "
        f"{'허용' if r['is_compliant'] else '위반/제한'} - {r['notes']}"
        for r in compliance_results
    )

    prompt = f"{REPORT_SYSTEM_PROMPT}\n\n성분별 규정 준수 결과:\n{results_text}"
    return structured_llm.invoke(prompt)

# ── DB: 국가 조회 ──
def get_country_names() -> list[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT country_name FROM country ORDER BY country_name;")
    names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return names


def get_country_id(country_name: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT country_id FROM country WHERE country_name = %s;",
        (country_name,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is None:
        raise ValueError(f"country 테이블에 '{country_name}'이(가) 없습니다.")
    return row[0]


# ── DB 저장: 수출 요청 + 검토 결과 ──
def save_export_request_and_result(
    product_id: int,
    country_id: int,
    risk_level: str,
    result_summary: str,
    recommendation: str,
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO export_request
                (product_id, country_id, request_status, source_type, completed_at)
            VALUES (%s, %s, 'COMPLETED', 'FILE', CURRENT_TIMESTAMP)
            RETURNING request_id;
            """,
            (product_id, country_id),
        )
        request_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO regulation_check_result
                (request_id, risk_level, result_summary, recommendation)
            VALUES (%s, %s, %s, %s);
            """,
            (request_id, risk_level, result_summary, recommendation),
        )
        conn.commit()
        return request_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()