-- 테스트용 Tibero DDL 샘플

-- 사용자 테이블
CREATE TABLE users (
    user_id NUMBER PRIMARY KEY,
    user_name VARCHAR2(100) NOT NULL,
    email VARCHAR2(200) UNIQUE,
    dept_id NUMBER,
    salary NUMBER,
    hire_date DATE DEFAULT SYSDATE,
    status VARCHAR2(10) DEFAULT 'ACTIVE'
);

-- 부서 테이블  
CREATE TABLE departments (
    dept_id NUMBER PRIMARY KEY,
    dept_name VARCHAR2(50) NOT NULL,
    manager_id NUMBER,
    location VARCHAR2(100),
    budget NUMBER
);

-- 급여 히스토리 테이블
CREATE TABLE salary_history (
    history_id NUMBER PRIMARY KEY,
    user_id NUMBER,
    old_salary NUMBER,
    new_salary NUMBER,
    change_date DATE DEFAULT SYSDATE,
    reason VARCHAR2(200)
);

-- 인덱스 생성
CREATE INDEX idx_users_dept ON users(dept_id);
CREATE INDEX idx_users_name ON users(user_name);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_salary_user ON salary_history(user_id);
CREATE INDEX idx_salary_date ON salary_history(change_date);
CREATE UNIQUE INDEX uk_dept_name ON departments(dept_name);

-- 외래키 관계
-- users.dept_id -> departments.dept_id
-- salary_history.user_id -> users.user_id
-- departments.manager_id -> users.user_id

-- 테이블 통계
-- users: 약 100,000건
-- departments: 약 50건  
-- salary_history: 약 500,000건
