import sys
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from src.nodes import check_ingredient_compliance

# 임시로 성분 하나만 테스트
test_ingredient = {"name": "Paprika extract", "e_number": "E160c"}

result = check_ingredient_compliance(test_ingredient)
print(result)