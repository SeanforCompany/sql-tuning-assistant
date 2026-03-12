# Tibero SQL 성능 튜닝 가이드

## 🎯 핵심 성능 최적화 전략

### 1. 인덱스 최적화
- **복합인덱스 순서**: 선택도가 높은 컬럼을 앞에 배치
- **WHERE 절 순서**: 인덱스 컬럼 순서와 일치시키기
- **함수 사용 금지**: WHERE절에서 컬럼에 함수 적용 시 인덱스 무효화
  ```sql
  -- 잘못된 예
  WHERE UPPER(user_name) = 'KIM'
  -- 올바른 예  
  WHERE user_name = 'KIM'
  ```

### 2. 조인 최적화
- **ANSI JOIN 사용**: WHERE절 조인보다 INNER JOIN 명시
- **조인 순서**: 작은 테이블을 먼저 조인
- **Tibero 힌트 활용**:
  ```sql
  /*+ USE_HASH(a b) */     -- 대용량 테이블 조인
  /*+ USE_NL(a b) */       -- 소용량 테이블 조인
  /*+ ORDERED */           -- FROM절 순서대로 조인
  ```

### 3. 서브쿼리 최적화
- **EXISTS vs IN**: 존재여부 확인 시 EXISTS 사용
- **JOIN 변환**: 상관 서브쿼리를 JOIN으로 변환
- **WITH절 활용**: 복잡한 서브쿼리는 CTE로 분리

### 4. SELECT절 최적화
- **필요한 컬럼만 선택**: SELECT * 지양 (단, 모든 컬럼이 필요한 경우는 예외)
- **집계함수 최적화**: 여러 집계함수를 한 번에 처리

### 5. Tibero 특화 기능
- **힌트 사용**:
  ```sql
  /*+ FIRST_ROWS */        -- OLTP 환경
  /*+ ALL_ROWS */          -- 배치 처리
  /*+ PARALLEL(4) */       -- 병렬 처리
  ```
- **날짜 함수**: SYSDATE, ADD_MONTHS, TRUNC 등 Tibero 최적화 함수 사용
- **ROWNUM**: 페이징 처리 시 OFFSET보다 효율적

## 🚫 피해야 할 안티패턴

1. **WHERE절에서 컬럼 가공**: `WHERE salary * 1.1 > 1000000`
2. **LIKE 앞쪽 와일드카드**: `WHERE name LIKE '%김%'`
3. **OR 조건 남발**: UNION ALL로 분리 검토
4. **불필요한 DISTINCT**: 중복 제거가 정말 필요한지 확인
5. **서브쿼리 중첩**: 3단계 이상 중첩 시 JOIN 검토

## 📊 성능 측정 방법

```sql
-- 실행계획 확인
EXPLAIN PLAN FOR 
SELECT ...;

-- 통계 정보 갱신
EXEC DBMS_STATS.GATHER_TABLE_STATS('OWNER','TABLE_NAME');
```
