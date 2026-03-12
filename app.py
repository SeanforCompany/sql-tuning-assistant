"""
SQL Query Tuning Assistant
Tibero 데이터베이스 SQL 쿼리 최적화 도구
"""

import streamlit as st
import requests
import json
from typing import Dict, Any, Tuple
import sqlparse
import difflib

# 페이지 설정
st.set_page_config(
    page_title="SQL Query Tuning Assistant",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# H-Chat API 설정
HCHAT_API_CONFIG = {
    "base_url": "https://internal-apigw-kr.hmg-corp.io/hchat-in/api/v3/claude/messages",
    "api_key": st.secrets.get("HCHAT_API_KEY", "483ac21c0fbad595d4e7e1c2517a1bae845b098c5252c98bd50f4355b0a01f2e"),
    "model": "claude-sonnet-4-5"  # 지원되는 모델로 수정
}

def get_tibero_optimization_hints(schema_ddl: str, query: str) -> str:
    """스키마 분석을 통해 Tibero 특화 최적화 힌트 생성"""
    hints = []
    
    query_upper = query.upper()
    schema_upper = schema_ddl.upper()
    
    # 인덱스 정보 추출
    index_info = []
    for line in schema_ddl.split('\n'):
        if 'CREATE INDEX' in line.upper() or 'CREATE UNIQUE INDEX' in line.upper():
            index_info.append(line.strip())
    
    # 테이블 크기 정보 추출
    table_stats = {}
    for line in schema_ddl.split('\n'):
        if '약' in line and '건' in line:
            # "-- users: 약 100,000건" 형태 파싱
            parts = line.replace('--', '').strip().split(':')
            if len(parts) == 2:
                table_name = parts[0].strip()
                if '약' in parts[1]:
                    size_str = parts[1].split('약')[1].replace('건', '').replace(',', '').strip()
                    try:
                        table_stats[table_name.upper()] = int(size_str)
                    except:
                        pass
    
    optimization_context = f"""
AVAILABLE INDEXES:
{chr(10).join(index_info) if index_info else "No explicit indexes found"}

TABLE STATISTICS:
{chr(10).join([f"- {table}: ~{size:,} rows" for table, size in table_stats.items()]) if table_stats else "No statistics provided"}

TIBERO OPTIMIZATION PRIORITIES:
1. Use existing indexes effectively (check WHERE clause column order)
2. For large tables (>100K rows): Consider hash joins with /*+ USE_HASH */ hint
3. For small tables (<1K rows): Consider nested loop with /*+ USE_NL */ hint  
4. Use /*+ FIRST_ROWS */ for OLTP queries, /*+ ALL_ROWS */ for batch processing
5. Replace correlated subqueries with JOINs when possible
6. Use EXISTS instead of IN for existence checks
7. Consider partitioning hints if tables are partitioned"""

    return optimization_context

def validate_sql_completeness(sql_query: str) -> Tuple[bool, str]:
    """SQL 쿼리의 완성도를 검증"""
    if not sql_query or not sql_query.strip():
        return False, "쿼리가 비어있습니다."
    
    sql_query = sql_query.strip()
    sql_upper = sql_query.upper()
    
    # 기본 SQL 키워드 체크
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'DROP', 'ALTER']
    if not any(keyword in sql_upper for keyword in sql_keywords):
        return False, "유효한 SQL 키워드가 없습니다."
    
    # 괄호 매칭 체크
    open_parens = sql_query.count('(')
    close_parens = sql_query.count(')')
    if open_parens != close_parens:
        return False, f"괄호가 일치하지 않습니다. ({open_parens}개 열림, {close_parens}개 닫힘)"
    
    # 따옴표 매칭 체크
    single_quotes = sql_query.count("'")
    if single_quotes % 2 != 0:
        return False, "작은따옴표가 일치하지 않습니다."
    
    # 불완전한 절 체크
    problematic_endings = [
        "GROUP BY", "ORDER BY", "HAVING", "WHERE", "SET", "VALUES", "FROM", "JOIN", "ON",
        "SELECT", "AND", "OR", "IN", "EXISTS", "BETWEEN", "LIKE"
    ]
    
    lines = sql_query.split('\n')
    last_meaningful_line = ""
    for line in reversed(lines):
        line = line.strip()
        if line and not line.startswith('--'):
            last_meaningful_line = line
            break
    
    # 마지막 줄이 문제가 있는 키워드로 끝나거나 쉼표로 끝나는지 체크
    if last_meaningful_line:
        for keyword in problematic_endings:
            if last_meaningful_line.upper().endswith(keyword):
                return False, f"쿼리가 '{keyword}'로 끝나 불완전합니다."
        
        if last_meaningful_line.endswith(','):
            return False, "쿼리가 쉼표로 끝나 불완전합니다."
    
    # sqlparse를 사용한 추가 검증
    try:
        parsed = sqlparse.parse(sql_query)
        if not parsed or not parsed[0].tokens:
            return False, "SQL 파싱에 실패했습니다."
    except Exception as e:
        return False, f"SQL 구문 오류: {str(e)}"
    
    return True, "쿼리가 완전합니다."

def initialize_session_state():
    """세션 상태 초기화"""
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'schema_ddl' not in st.session_state:
        st.session_state.schema_ddl = ""
    if 'original_query' not in st.session_state:
        st.session_state.original_query = ""
    if 'optimized_query' not in st.session_state:
        st.session_state.optimized_query = ""
    if 'optimization_comments' not in st.session_state:
        st.session_state.optimization_comments = []

def call_claude_api(schema_ddl: str, original_query: str) -> Dict[str, Any]:
    """Claude API 호출하여 SQL 쿼리 최적화"""
    
    system_message = """You are a Tibero database performance tuning expert with 10+ years of experience.
    Your goal is to optimize SQL queries for REAL performance improvement, not cosmetic changes.
    
    CRITICAL PERFORMANCE OPTIMIZATION RULES:
    
    1. INDEX USAGE OPTIMIZATION:
       - Always check if existing indexes can be utilized
       - Suggest new indexes only if absolutely necessary
       - Ensure WHERE clause conditions match index columns in order
       - Use composite indexes effectively (most selective column first)
    
    2. JOIN OPTIMIZATION:
       - Always use INNER JOIN instead of WHERE-based joins when possible  
       - Order joins by table size (smaller table first in most cases)
       - Use proper join hints for Tibero: /*+ USE_NL */, /*+ USE_HASH */
       - Avoid unnecessary self-joins
    
    3. WHERE CLAUSE OPTIMIZATION:
       - Move most selective conditions first
       - Use EXISTS instead of IN for subqueries when checking existence
       - Avoid functions in WHERE clause that prevent index usage
       - Use proper date comparisons for Tibero
    
    4. SELECT CLAUSE OPTIMIZATION:
       - Replace SELECT * with specific columns ONLY if it reduces I/O significantly
       - Keep SELECT * if all columns are actually needed
    
    5. TIBERO-SPECIFIC OPTIMIZATIONS:
       - Use proper hints: /*+ FIRST_ROWS */, /*+ ALL_ROWS */
       - Consider ROWNUM for pagination instead of OFFSET
       - Use proper date functions: SYSDATE, ADD_MONTHS, TRUNC
       - Leverage Tibero's optimizer statistics
    
    6. SUBQUERY OPTIMIZATION:
       - Convert correlated subqueries to JOINs when possible
       - Use WITH clause (CTE) for complex repeated logic
       - Consider window functions instead of self-joins
    
    AVOID THESE COSMETIC CHANGES:
    - Don't change query logic unnecessarily
    - Don't add comments that don't improve performance
    - Don't modify column order unless it impacts performance
    - Don't change alias names for no reason
    
    Return format:
    ORIGINAL_QUERY:
    {original_query}
    
    OPTIMIZED_QUERY:
    [Complete optimized query with Tibero-specific performance improvements]
    
    PERFORMANCE_IMPROVEMENTS:
    1. [Specific performance gain explanation with estimated impact]
    2. [Index usage improvement]
    3. [Join optimization benefit]
    4. [I/O reduction details]
    
    END_RESPONSE"""
    
    # 스키마 분석을 통한 최적화 컨텍스트 생성
    optimization_context = get_tibero_optimization_hints(schema_ddl, original_query)
    
    user_message = f"""
{optimization_context}

ORIGINAL QUERY TO OPTIMIZE:
{original_query}

OPTIMIZATION REQUEST:
- Analyze the query execution path and identify bottlenecks
- Apply Tibero-specific performance optimizations
- Focus ONLY on changes that provide measurable speed improvements
- Maintain exact same query results and business logic
- Provide estimated performance improvement percentages
- Suggest specific index usage strategies"""

    payload = {
        "max_tokens": 4000,  # 토큰 수 증가
        "model": HCHAT_API_CONFIG["model"],
        "stream": False,
        "system": system_message,
        "messages": [
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": HCHAT_API_CONFIG["api_key"]
    }
    
    try:
        response = requests.post(
            HCHAT_API_CONFIG["base_url"],
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False, 
                "error": f"API 호출 실패: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {"success": False, "error": f"네트워크 오류: {str(e)}"}

def parse_claude_response(response_text: str) -> Tuple[str, str, list]:
    """Claude 응답을 파싱하여 원본쿼리, 최적화쿼리, 변경사항을 추출"""
    try:
        # 응답 정규화
        response_text = response_text.strip()
        
        # 각 섹션 추출
        original_query = ""
        optimized_query = ""
        comments = []
        
        # ORIGINAL_QUERY 섹션 추출
        if "ORIGINAL_QUERY:" in response_text:
            original_start = response_text.find("ORIGINAL_QUERY:") + len("ORIGINAL_QUERY:")
            original_end = response_text.find("OPTIMIZED_QUERY:")
            if original_end != -1:
                original_query = response_text[original_start:original_end].strip()
        
        # OPTIMIZED_QUERY 섹션 추출
        if "OPTIMIZED_QUERY:" in response_text:
            optimized_start = response_text.find("OPTIMIZED_QUERY:") + len("OPTIMIZED_QUERY:")
            optimized_end = response_text.find("CHANGES_MADE:")
            if optimized_end != -1:
                optimized_query = response_text[optimized_start:optimized_end].strip()
            else:
                # CHANGES_MADE가 없는 경우 END_RESPONSE까지 또는 끝까지
                end_marker = response_text.find("END_RESPONSE")
                if end_marker != -1:
                    optimized_query = response_text[optimized_start:end_marker].strip()
                else:
                    optimized_query = response_text[optimized_start:].strip()
        
        # PERFORMANCE_IMPROVEMENTS 섹션 추출 (CHANGES_MADE 대신)
        if "PERFORMANCE_IMPROVEMENTS:" in response_text:
            changes_start = response_text.find("PERFORMANCE_IMPROVEMENTS:") + len("PERFORMANCE_IMPROVEMENTS:")
            changes_end = response_text.find("END_RESPONSE")
            if changes_end != -1:
                changes_text = response_text[changes_start:changes_end].strip()
            else:
                changes_text = response_text[changes_start:].strip()
            
            # 번호가 있는 항목들 추출
            for line in changes_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # 번호나 대시 제거
                    clean_line = line.lstrip('0123456789. -').strip()
                    if clean_line:
                        comments.append(clean_line)
        
        # 폴백: CHANGES_MADE 섹션도 지원
        elif "CHANGES_MADE:" in response_text:
            changes_start = response_text.find("CHANGES_MADE:") + len("CHANGES_MADE:")
            changes_end = response_text.find("END_RESPONSE")
            if changes_end != -1:
                changes_text = response_text[changes_start:changes_end].strip()
            else:
                changes_text = response_text[changes_start:].strip()
            
            # 번호가 있는 항목들 추출
            for line in changes_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # 번호나 대시 제거
                    clean_line = line.lstrip('0123456789. -').strip()
                    if clean_line:
                        comments.append(clean_line)
        
        # 폴백: 기존 SQL 블록 방식도 지원
        if not optimized_query and "```sql" in response_text:
            sql_blocks = response_text.split("```sql")
            if len(sql_blocks) > 1:
                sql_content = sql_blocks[1].split("```")[0].strip()
                
                # SQL 블록에서 원본과 최적화 쿼리 분리
                lines = sql_content.split('\n')
                current_section = None
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("-- Original Query") or line.startswith("--Original Query"):
                        current_section = "original"
                        continue
                    elif line.startswith("-- Optimized Query") or line.startswith("--Optimized Query"):
                        current_section = "optimized"
                        continue
                    elif line.startswith("-- Changes") or line.startswith("--Changes"):
                        current_section = "comments"
                        continue
                    elif line.startswith("--"):
                        if current_section == "comments":
                            comments.append(line[2:].strip())
                        continue
                        
                    if current_section == "original" and line:
                        original_query += line + "\n"
                    elif current_section == "optimized" and line:
                        optimized_query += line + "\n"
        
        # 쿼리 검증
        if optimized_query:
            is_valid, validation_msg = validate_sql_completeness(optimized_query)
            if not is_valid:
                return original_query.strip(), "", [f"쿼리 검증 실패: {validation_msg}"]
        
        return original_query.strip(), optimized_query.strip(), comments
        
    except Exception as e:
        return "", "", [f"응답 파싱 오류: {str(e)}. 원본 응답을 확인해주세요."]

def main():
    """메인 애플리케이션"""
    initialize_session_state()
    
    # 헤더
    st.title("🔧 SQL Query Tuning Assistant")
    st.markdown("**Tibero 데이터베이스 SQL 쿼리 최적화 도구**")
    
    # 사이드바 - 진행 상황
    with st.sidebar:
        st.header("📋 진행 상황")
        
        steps = ["1️⃣ DB 스키마 입력", "2️⃣ 쿼리 입력", "3️⃣ 결과 비교"]
        for i, step in enumerate(steps, 1):
            if i == st.session_state.current_step:
                st.markdown(f"**➤ {step}**")
            elif i < st.session_state.current_step:
                st.markdown(f"✅ {step}")
            else:
                st.markdown(f"⏸️ {step}")
                
        st.divider()
        
        if st.button("🔄 처음부터 다시"):
            for key in ['current_step', 'schema_ddl', 'original_query', 'optimized_query', 'optimization_comments']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Step 1: DB 스키마 입력
    if st.session_state.current_step == 1:
        show_step1_schema_input()
    
    # Step 2: 쿼리 입력
    elif st.session_state.current_step == 2:
        show_step2_query_input()
    
    # Step 3: 결과 비교
    elif st.session_state.current_step == 3:
        show_step3_results()

def show_step1_schema_input():
    """Step 1: DB 스키마 입력 페이지"""
    st.header("1️⃣ DB 스키마 정보 입력")
    st.markdown("튜닝할 쿼리와 관련된 테이블들의 DDL 정보를 입력해주세요. (다중 테이블 지원)")
    
    # 예시 템플릿 제공
    with st.expander("💡 입력 예시 보기"):
        st.code("""-- 테이블 정의
CREATE TABLE users (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    dept_id NUMBER,
    created_date DATE DEFAULT SYSDATE
);

CREATE TABLE departments (
    id NUMBER PRIMARY KEY,
    dept_name VARCHAR2(50) NOT NULL,
    manager_id NUMBER
);

-- 인덱스 정보
CREATE INDEX idx_users_dept ON users(dept_id);
CREATE INDEX idx_users_name ON users(name);
CREATE UNIQUE INDEX uk_dept_name ON departments(dept_name);

-- 테이블 통계 (선택사항)
-- users: 약 1,000,000건
-- departments: 약 100건

-- 외래키 관계
-- users.dept_id -> departments.id""", language="sql")
    
    # DDL 입력
    schema_ddl = st.text_area(
        "DDL 정보 입력:",
        value=st.session_state.schema_ddl,
        height=400,
        placeholder="CREATE TABLE ... 형식으로 입력해주세요"
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✅ 다음 단계로", type="primary", disabled=not schema_ddl.strip()):
            st.session_state.schema_ddl = schema_ddl
            st.session_state.current_step = 2
            st.rerun()
    
    with col2:
        if schema_ddl.strip():
            st.success(f"입력된 DDL: {len(schema_ddl)} 글자")

def show_step2_query_input():
    """Step 2: 쿼리 입력 페이지"""
    st.header("2️⃣ SQL 쿼리 입력")
    st.markdown("최적화하고 싶은 SQL 쿼리를 입력해주세요.")
    
    # 스키마 정보 요약 표시
    with st.expander("📋 입력된 스키마 정보 요약"):
        st.code(st.session_state.schema_ddl, language="sql")
    
    # SQL 쿼리 입력
    original_query = st.text_area(
        "최적화할 SQL 쿼리:",
        value=st.session_state.original_query,
        height=300,
        placeholder="SELECT * FROM users WHERE ..."
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ 이전 단계"):
            st.session_state.current_step = 1
            st.rerun()
    
    with col2:
        if st.button("🔍 쿼리 분석 및 튜닝", type="primary", disabled=not original_query.strip()):
            st.session_state.original_query = original_query
            
            # 재시도 로직
            max_retries = 3
            for attempt in range(max_retries):
                with st.spinner(f"Claude AI가 쿼리를 분석하고 최적화하는 중... (시도 {attempt + 1}/{max_retries})"):
                    result = call_claude_api(st.session_state.schema_ddl, original_query)
                    
                    if result["success"]:
                        try:
                            # Claude 응답에서 content 추출
                            response_content = result["data"]["content"][0]["text"]
                            
                            # 응답 파싱
                            orig, optimized, comments = parse_claude_response(response_content)
                            
                            # 최적화된 쿼리 검증
                            if optimized and len(optimized.strip()) > 10:  # 최소 길이 체크
                                # 추가 검증: 기본적인 SQL 키워드 포함 확인
                                optimized_upper = optimized.upper()
                                if any(keyword in optimized_upper for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
                                    st.session_state.optimized_query = optimized
                                    st.session_state.optimization_comments = comments
                                    st.session_state.current_step = 3
                                    st.rerun()
                                    break
                                else:
                                    st.warning(f"시도 {attempt + 1}: 유효하지 않은 SQL 쿼리가 생성되었습니다.")
                            else:
                                st.warning(f"시도 {attempt + 1}: 완전하지 않은 쿼리가 생성되었습니다.")
                                
                            # 마지막 시도가 실패한 경우
                            if attempt == max_retries - 1:
                                st.error("최적화에 실패했습니다. 원본 응답을 표시합니다.")
                                st.session_state.optimized_query = response_content
                                st.session_state.optimization_comments = ["완전한 최적화 실패 - 원본 AI 응답 표시"]
                                st.session_state.current_step = 3
                                st.rerun()
                                
                        except Exception as e:
                            if attempt == max_retries - 1:
                                st.error(f"응답 처리 중 오류 발생: {str(e)}")
                                with st.expander("디버깅 정보"):
                                    st.json(result["data"])
                            else:
                                st.warning(f"시도 {attempt + 1}: 응답 처리 오류 - 재시도 중...")
                    else:
                        if attempt == max_retries - 1:
                            st.error(result["error"])
                        else:
                            st.warning(f"시도 {attempt + 1}: API 호출 실패 - 재시도 중...")
    
    with col3:
        if original_query.strip():
            # 간단한 SQL 문법 검증
            try:
                parsed = sqlparse.parse(original_query)
                if parsed:
                    st.success("✅ SQL 문법 검증 통과")
                else:
                    st.warning("⚠️ SQL 문법을 확인해주세요")
            except:
                st.warning("⚠️ SQL 문법을 확인해주세요")

def show_step3_results():
    """Step 3: 결과 비교 페이지"""
    st.header("3️⃣ 쿼리 최적화 결과")
    
    # 상단 버튼들
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ 쿼리 수정"):
            st.session_state.current_step = 2
            st.rerun()
    
    with col2:
        if st.button("🔄 다시 튜닝"):
            with st.spinner("재분석 중..."):
                result = call_claude_api(st.session_state.schema_ddl, st.session_state.original_query)
                if result["success"]:
                    response_content = result["data"]["content"][0]["text"]
                    orig, optimized, comments = parse_claude_response(response_content)
                    st.session_state.optimized_query = optimized if optimized else response_content
                    st.session_state.optimization_comments = comments
                    st.rerun()
    
    with col3:
        if st.download_button(
            "💾 결과 다운로드",
            data=f"-- 원본 쿼리\n{st.session_state.original_query}\n\n-- 최적화된 쿼리\n{st.session_state.optimized_query}\n\n-- 변경사항\n" + "\n".join([f"-- {comment}" for comment in st.session_state.optimization_comments]),
            file_name="sql_optimization_result.sql",
            mime="text/plain"
        ):
            st.success("결과가 다운로드되었습니다!")
    
    st.divider()
    
    # 좌우 분할 비교 화면
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📝 원본 쿼리 (Before)")
        st.code(st.session_state.original_query, language="sql")
    
    with col_right:
        st.subheader("⚡ 최적화된 쿼리 (After)")
        
        # 쿼리 상태 표시
        if st.session_state.optimized_query:
            try:
                # SQL 파싱을 통한 유효성 검사
                parsed = sqlparse.parse(st.session_state.optimized_query)
                if parsed and parsed[0].tokens:
                    st.success("✅ 유효한 SQL 쿼리")
                else:
                    st.warning("⚠️ 쿼리 구문을 확인해주세요")
            except:
                st.warning("⚠️ 쿼리 구문을 확인해주세요")
        
        st.code(st.session_state.optimized_query, language="sql")
        
        # 쿼리 복사 버튼
        if st.button("📋 최적화된 쿼리 복사"):
            st.code(st.session_state.optimized_query, language="sql")
            st.success("쿼리가 위에 표시되었습니다. 복사해서 사용하세요!")
    
    # 변경사항 설명
    if st.session_state.optimization_comments:
        st.subheader("� 성능 최적화 개선사항")
        
        # 성능 개선 정보를 카테고리별로 분류
        performance_categories = {
            "인덱스 최적화": [],
            "조인 최적화": [], 
            "I/O 개선": [],
            "기타 최적화": []
        }
        
        for comment in st.session_state.optimization_comments:
            comment_lower = comment.lower()
            if any(keyword in comment_lower for keyword in ['index', '인덱스', 'idx']):
                performance_categories["인덱스 최적화"].append(comment)
            elif any(keyword in comment_lower for keyword in ['join', '조인', 'hash', 'nested']):
                performance_categories["조인 최적화"].append(comment)
            elif any(keyword in comment_lower for keyword in ['i/o', 'scan', 'select *', '스캔']):
                performance_categories["I/O 개선"].append(comment)
            else:
                performance_categories["기타 최적화"].append(comment)
        
        # 카테고리별 표시
        col1, col2 = st.columns(2)
        
        with col1:
            for category, items in list(performance_categories.items())[:2]:
                if items:
                    st.markdown(f"**{category}**")
                    for item in items:
                        st.markdown(f"• {item}")
        
        with col2:
            for category, items in list(performance_categories.items())[2:]:
                if items:
                    st.markdown(f"**{category}**")
                    for item in items:
                        st.markdown(f"• {item}")
        
        # 전체 리스트도 제공
        with st.expander("📋 전체 최적화 내역 보기"):
            for i, comment in enumerate(st.session_state.optimization_comments, 1):
                st.markdown(f"**{i}.** {comment}")
    else:
        st.info("성능 최적화 정보가 없습니다.")
    
    # 추가 분석 도구
    st.subheader("🔍 추가 분석")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 쿼리 복잡도 비교"):
            original_complexity = len(st.session_state.original_query.split())
            optimized_complexity = len(st.session_state.optimized_query.split())
            
            st.metric(
                label="쿼리 복잡도 변화",
                value=f"{optimized_complexity} 단어", 
                delta=f"{optimized_complexity - original_complexity} 단어"
            )
    
    with col2:
        if st.button("🎯 핵심 개선점 요약"):
            if st.session_state.optimization_comments:
                # 핵심 키워드 추출
                key_improvements = []
                for comment in st.session_state.optimization_comments:
                    if any(keyword in comment.lower() for keyword in ['%', '배', '시간', '성능']):
                        key_improvements.append(comment)
                
                if key_improvements:
                    st.success("🎯 **핵심 성능 개선점**")
                    for improvement in key_improvements[:3]:  # 상위 3개만 표시
                        st.markdown(f"✅ {improvement}")
                else:
                    st.info("구체적인 성능 수치가 포함된 개선사항이 없습니다.")
    
    st.divider()
    with st.expander("🔍 상세 차이점 분석"):
        original_lines = st.session_state.original_query.splitlines()
        optimized_lines = st.session_state.optimized_query.splitlines()
        
        diff = list(difflib.unified_diff(
            original_lines, 
            optimized_lines,
            fromfile="Original Query",
            tofile="Optimized Query",
            lineterm=""
        ))
        
        if diff:
            st.code('\n'.join(diff), language="diff")
        else:
            st.info("쿼리가 동일하거나 차이점을 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
