# SQL Query Tuning Assistant

Tibero 데이터베이스 SQL 쿼리 최적화 도구

## 🎯 기능

- **3단계 워크플로우**: 스키마 입력 → 쿼리 입력 → 최적화 결과 비교
- **AI 기반 튜닝**: H-Chat Claude 모델을 활용한 지능형 SQL 최적화
- **Tibero 특화**: Tibero 데이터베이스에 최적화된 성능 튜닝
- **실시간 비교**: Before/After 쿼리 비교 및 개선사항 상세 설명

## 🚀 사용법

### 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

### 웹 접속
배포된 앱: [SQL Tuning Assistant](https://sql-tuning-assistant.streamlit.app)

## 📋 Step-by-Step 가이드

1. **Step 1: DB 스키마 입력**
   - DDL 형식으로 테이블 구조 입력
   - 인덱스 정보 및 테이블 통계 포함

2. **Step 2: 쿼리 입력** 
   - 최적화하고 싶은 SQL 쿼리 입력
   - AI가 자동으로 성능 분석 및 튜닝 수행

3. **Step 3: 결과 확인**
   - 원본 vs 최적화된 쿼리 비교
   - 구체적인 성능 개선사항 설명
   - 다운로드 및 복사 기능

## 🔧 기술 스택

- **Frontend**: Streamlit
- **AI Model**: H-Chat Claude (사내 API)
- **Database**: Tibero
- **Language**: Python

## ⚙️ 환경 설정

환경변수로 다음 값을 설정해야 합니다:
- `HCHAT_API_KEY`: H-Chat API 인증키

## 📝 샘플

프로젝트에는 테스트용 샘플 스키마와 쿼리가 포함되어 있습니다:
- `sample_schema.sql`: 테스트용 테이블 구조
- `sample_queries.sql`: 튜닝 테스트용 쿼리
- `performance_problem_queries.sql`: 성능 문제가 있는 쿼리 예시

---

**🎯 회사 내부 도구로 개발된 SQL 성능 최적화 시스템입니다.**
