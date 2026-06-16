# ZipFit
서울여자대학교 빅데이터분석 수업 기말프로젝트 
공공데이터 6종을 법정동 단위로 융합한 개인화 거주지 추천 서비스 | Python · Streamlit · Plotly

## Streamlit keep-alive 설정

Streamlit Community Cloud 무료 배포는 일정 시간 접속자가 없으면 앱이 슬립 상태로 전환될 수 있습니다. 이 저장소에는 GitHub Actions가 6시간마다 앱의 가벼운 헬스체크 주소를 호출하는 워크플로가 포함되어 있습니다.

1. GitHub 저장소의 `Settings > Secrets and variables > Actions`로 이동합니다.
2. `New repository secret`을 눌러 `STREAMLIT_APP_URL`을 추가합니다.
3. 값에는 배포된 Streamlit 앱 주소를 넣습니다. 예: `https://your-app.streamlit.app`

앱은 `?health=1` 요청을 받으면 CSV와 차트를 로드하지 않고 `ok`만 응답합니다.
서울여자대학교 빅데이터분석 수업 기말프로젝트 (데이터분석 및 시각화)
- 공공데이터 6종을 법정동 단위로 융합한 개인화 거주지 추천 서비스 | Python · Streamlit · Plotly
