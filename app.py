# -*- coding: utf-8 -*-
# =========================================================
# 우리동네 거주지 추천 서비스 (Streamlit)
#   merged_score_by_region.csv (600행, rank/log 정규화 완료) 사용
#   포함: 페르소나4 · 가중치슬라이더6 · 지역필터 · plotly지도
#         · 동 선택 레이더차트 · 내 동네 검색
# 실행: streamlit run app.py
# =========================================================
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="우리동네 거주지 추천", page_icon="🏠")


def is_healthcheck_request():
    try:
        return st.query_params.get("health") == "1"
    except AttributeError:
        return st.experimental_get_query_params().get("health", [""])[0] == "1"


if is_healthcheck_request():
    st.write("ok")
    st.stop()

# ---------------------------------------------------------
# 데이터 로드
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "merged_score_by_region.csv"


@st.cache_data(show_spinner="데이터를 불러오는 중입니다...")
def load_data():
    if not DATA_PATH.exists():
        st.error(f"데이터 파일을 찾을 수 없습니다: {DATA_PATH.name}")
        st.stop()

    # 첫 줄이 제목 줄(법정동코드 없음)이면 건너뛰고 읽음
    with DATA_PATH.open(encoding="utf-8-sig") as f:
        first = f.readline()
    header_row = 0 if "법정동코드" in first else 1

    df = pd.read_csv(DATA_PATH, dtype={"법정동코드": str},
                     encoding="utf-8-sig", header=header_row)
    df.columns = df.columns.str.strip()
    df["법정동코드"] = df["법정동코드"].str.zfill(10)
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    return df.dropna(subset=["위도", "경도"])

df = load_data()

CATS = ["가격점수", "교통점수", "교육점수", "의료점수", "공원점수", "치안점수"]
LABELS = {c: c.replace("점수", "") for c in CATS}

# 페르소나별 기본 가중치 (슬라이더 초기값)
PRESETS = {
    "🎓 1인가구 (대학생)": {"가격점수":.35,"교통점수":.25,"교육점수":.05,"의료점수":.05,"공원점수":.10,"치안점수":.20},
    "💼 1인가구 (직장인)": {"가격점수":.25,"교통점수":.35,"교육점수":.05,"의료점수":.05,"공원점수":.10,"치안점수":.20},
    "👨‍👩‍👧 가족 (자녀있음)": {"가격점수":.15,"교통점수":.15,"교육점수":.30,"의료점수":.15,"공원점수":.10,"치안점수":.15},
    "👵 가족 (노년)":       {"가격점수":.15,"교통점수":.10,"교육점수":.05,"의료점수":.35,"공원점수":.20,"치안점수":.15},
}

# ---------------------------------------------------------
# session_state 초기화
# ---------------------------------------------------------
if "init" not in st.session_state:
    for c, v in PRESETS["🎓 1인가구 (대학생)"].items():
        st.session_state[f"w_{c}"] = v
    st.session_state["init"] = True

def apply_preset(name):
    for c, v in PRESETS[name].items():
        st.session_state[f"w_{c}"] = v

# ---------------------------------------------------------
# 사이드바: 페르소나 + 슬라이더 + 지역 필터
# ---------------------------------------------------------
with st.sidebar:
    st.title("🏠 우리동네 거주지 추천")
    st.caption("서울·경기 600개 법정동 · 6개 생활 인프라 기준")

    st.markdown("### 누구를 위한 추천인가요?")
    for name in PRESETS:
        st.button(name, on_click=apply_preset, args=(name,),
                  use_container_width=True)

    st.markdown("### 무엇을 중요하게 볼까요?")
    st.caption("슬라이더를 높일수록 그 요소를 우선해서 추천해요")

    # 슬라이더 아래에 표시할 양끝 의미 (무관 ←→ 우선)
    MEANING = {
        "가격점수": "💰 무관 ←──→ 저렴한 동네 우선",
        "교통점수": "🚇 무관 ←──→ 역세권 우선",
        "교육점수": "📚 무관 ←──→ 학군 좋은 동네 우선",
        "의료점수": "🏥 무관 ←──→ 병원 많은 동네 우선",
        "공원점수": "🌳 무관 ←──→ 공원 많은 동네 우선",
        "치안점수": "🛡️ 무관 ←──→ 치안 인프라 우선",
    }
    w = {}
    for c in CATS:
        w[c] = st.slider(LABELS[c], 0.0, 1.0, step=0.05, key=f"w_{c}")
        st.caption(MEANING[c])

    st.markdown("### 지역")
    region = st.radio("지역 선택", ["전체", "서울특별시", "경기도"],
                      horizontal=True, label_visibility="collapsed")

# ---------------------------------------------------------
# 종합점수 재계산 + 지역 필터
# ---------------------------------------------------------
wsum = sum(w.values()) or 1
view = df.copy()
if region != "전체":
    view = view[view["시도"] == region]
view["종합점수"] = sum(view[c] * w[c] for c in CATS) / wsum
view = view.sort_values("종합점수", ascending=False).reset_index(drop=True)
view["순위"] = view.index + 1
top10 = view.head(10)

# ---------------------------------------------------------
# 메인 레이아웃
# ---------------------------------------------------------
st.markdown("## 추천 결과")
left, right = st.columns([5, 4])

# ----- 좌: Top 10 테이블 + 지도 -----
with left:
    st.markdown("#### 🏆 Top 10 추천 지역")
    show = top10[["순위", "법정동명", "종합점수"] + CATS].copy()
    show.columns = ["순위", "법정동명", "종합"] + [LABELS[c] for c in CATS]
    st.dataframe(show.round(1), hide_index=True, use_container_width=True)

    st.markdown("#### 🗺️ 지도 (점수 높을수록 진하고 큼)")
    fig_map = px.scatter_mapbox(
        top10, lat="위도", lon="경도",
        color="종합점수", size="종합점수",
        text="법정동명",
        hover_name="법정동명",
        hover_data={"종합점수": ":.1f", "시군구": True,
                    "위도": False, "경도": False, "법정동명": False},
        color_continuous_scale="Turbo", size_max=28, zoom=9.3, height=480,
    )
    fig_map.update_traces(textposition="top center",
                          textfont=dict(size=11, color="#222"))
    fig_map.update_layout(mapbox_style="open-street-map",
                          margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

# ----- 우: 동 선택 → 레이더 차트 -----
with right:
    st.markdown("#### 📍 지역 상세 보기")
    sel = st.selectbox("동을 선택하세요", top10["법정동명"].tolist())
    row = view[view["법정동명"] == sel].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("종합점수", f"{row['종합점수']:.1f}")
    c2.metric("순위", f"{int(row['순위'])}위")
    price = row.get("평균거래가_억")
    c3.metric("평균 실거래가", f"{price:.1f}억" if pd.notna(price) else "—")

    # 레이더 차트 (6개 항목)
    radar_vals = [row[c] for c in CATS] + [row[CATS[0]]]
    radar_lbls = [LABELS[c] for c in CATS] + [LABELS[CATS[0]]]
    # 치안은 '인프라' 명시
    radar_lbls = [l if l != "치안" else "치안(인프라)" for l in radar_lbls]
    fig_radar = go.Figure(go.Scatterpolar(
        r=radar_vals, theta=radar_lbls, fill="toself",
        line_color="#E8743B", fillcolor="rgba(232,116,59,0.3)"))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=360, margin=dict(l=40, r=40, t=20, b=20))
    st.plotly_chart(fig_radar, use_container_width=True)

    # 왜 추천됐는지 — 상위 2개 강점
    strengths = sorted([(LABELS[c], row[c]) for c in CATS],
                       key=lambda x: -x[1])[:2]
    st.info(f"**{sel}**의 강점: "
            + ", ".join(f"{n} {v:.0f}점" for n, v in strengths))

# ---------------------------------------------------------
# 하단: 내 동네 검색
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 🔍 내 동네는 몇 위?")
q = st.text_input("동 이름을 입력하세요", placeholder="예: 역삼동, 상계동, 분당")
if q:
    hit = view[view["법정동명"].str.contains(q, na=False)]
    if len(hit):
        r = hit.iloc[0]
        total = len(view)
        pct = round(r["순위"] / total * 100)
        a, b, c, d = st.columns(4)
        a.metric(r["법정동명"].split()[-1], f"{int(r['순위'])}위")
        b.metric("전체", f"{total}개 중")
        c.metric("상위", f"{pct}%")
        rp = r.get("평균거래가_억")
        d.metric("평균가", f"{rp:.1f}억" if pd.notna(rp) else "—")
        # 6개 점수 막대
        bars = pd.DataFrame({"항목": [LABELS[x] for x in CATS],
                             "점수": [r[x] for x in CATS]})
        fig_bar = px.bar(bars, x="점수", y="항목", orientation="h",
                         range_x=[0, 100], height=280,
                         color="점수", color_continuous_scale="YlOrRd")
        fig_bar.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                              coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning(f"'{q}' 검색 결과가 없어요. (현재 지역 필터: {region})")

st.caption("※ 점수는 동들 사이의 상대적 위치(백분위·log 스케일)입니다. "
           "치안은 CCTV·경찰 등 '치안 인프라' 밀도로, 체감 안전과는 다를 수 있습니다.")
