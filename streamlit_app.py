import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from src.state import AgentState
from src.nodes import extraction_node, compliance_node, report_node, save_result_node
from src.tools import get_country_names

st.set_page_config(
    page_title="EU 식품 수출 규정 검토",
    page_icon="🇪🇺",
    layout="centered",
)

st.title("EU 식품 수출 규정 검토 시스템")
st.caption("제품 성분표를 업로드하면, EU 수출 가능 여부를 AI가 자동으로 판단해드립니다.")

st.divider()

country = st.selectbox("수출 대상 국가", get_country_names())

uploaded_file = st.file_uploader(
    "성분표 파일을 업로드하세요",
    type=["txt"],
    help="현재는 .txt 형식만 지원합니다.",
)

if uploaded_file is not None:
    st.info(f"📄 업로드된 파일: **{uploaded_file.name}** / 🌍 수출 대상: **{country}**")

    if st.button("🔍 규정 검토 시작", type="primary", use_container_width=True):
        os.makedirs("uploads", exist_ok=True)
        temp_path = f"uploads/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        state: AgentState = {
            "messages": [],
            "file_path": temp_path,
            "country": country,
            "product_id": None,
            "raw_document": None,
            "ingredients": None,
            "regulation_findings": None,
            "compliance_result": None,
            "report": None,
            "report_data": None,
        }

        with st.status("검토 진행 중...", expanded=True) as status:
            st.write("1️⃣ 성분표에서 정보 추출 중...")
            state.update(extraction_node(state))
            st.write(f"　　✅ 성분 {len(state['ingredients'])}개 추출 완료")

            st.write("2️⃣ EU 규정 데이터베이스에서 성분별 준수 여부 확인 중...")
            state.update(compliance_node(state))
            st.write("　　✅ 규정 검토 완료")

            st.write("3️⃣ 최종 리포트 작성 중...")
            state.update(report_node(state))
            st.write("　　✅ 리포트 작성 완료")

            st.write("4️⃣ 검토 결과를 데이터베이스에 저장 중...")
            state.update(save_result_node(state))
            st.write("　　✅ 저장 완료")

            status.update(label="✅ 검토 완료!", state="complete", expanded=False)

        st.divider()

        results = state["compliance_result"]["ingredients"]
        total = len(results)
        compliant = sum(1 for r in results if r["is_compliant"])
        violations = total - compliant

        col1, col2, col3 = st.columns(3)
        col1.metric("전체 성분", f"{total}개")
        col2.metric("✅ 허용", f"{compliant}개")
        col3.metric("❌ 위반/제한", f"{violations}개")

        st.divider()

        st.subheader("📋 최종 리포트")
        st.markdown(state["report"])

        with st.expander("🔎 성분별 상세 검토 결과 보기"):
            for r in results:
                icon = "✅" if r["is_compliant"] else "❌"
                st.markdown(f"**{icon} {r['ingredient_name']}** ({r.get('e_number') or 'E-번호 없음'})")
                st.caption(r["notes"])
                st.markdown("---")