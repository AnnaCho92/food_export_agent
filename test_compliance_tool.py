import sys
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from src.compliance_tools import search_regulation

result = search_regulation.invoke("E160c 파프리카 추출물 사용 기준")
print(result)