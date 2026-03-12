-- 성능 튜닝에 특화된 문제적 쿼리 샘플들

-- 쿼리 1: 인덱스를 활용하지 못하는 WHERE 조건
SELECT u.user_name, u.salary, d.dept_name
FROM users u, departments d 
WHERE u.dept_id = d.dept_id
  AND UPPER(u.user_name) LIKE '%KIM%'
  AND u.salary * 1.1 > 5000000
  AND EXTRACT(YEAR FROM u.hire_date) = 2023;

-- 쿼리 2: 비효율적인 서브쿼리 (N+1 문제)
SELECT d.dept_name, 
       (SELECT COUNT(*) FROM users WHERE dept_id = d.dept_id) as user_count,
       (SELECT AVG(salary) FROM users WHERE dept_id = d.dept_id) as avg_salary,
       (SELECT MAX(hire_date) FROM users WHERE dept_id = d.dept_id) as latest_hire
FROM departments d
WHERE d.budget > 1000000;

-- 쿼리 3: 대용량 테이블 풀스캔 유발 쿼리
SELECT u.user_name, u.email, sh.new_salary
FROM users u
JOIN salary_history sh ON u.user_id = sh.user_id
WHERE sh.change_date BETWEEN '2023-01-01' AND '2023-12-31'
  AND u.status = 'ACTIVE'
  AND sh.new_salary > (SELECT AVG(new_salary) FROM salary_history)
ORDER BY sh.change_date DESC;

-- 쿼리 4: 비효율적인 EXISTS vs IN 사용
SELECT u.user_name, u.dept_id, u.salary
FROM users u
WHERE u.dept_id IN (
    SELECT d.dept_id 
    FROM departments d 
    WHERE d.location = 'SEOUL'
)
AND u.user_id IN (
    SELECT sh.user_id
    FROM salary_history sh
    WHERE sh.change_date > ADD_MONTHS(SYSDATE, -6)
);

-- 쿼리 5: 비효율적인 GROUP BY와 HAVING
SELECT d.dept_name, COUNT(u.user_id) as cnt, SUM(u.salary) as total_sal
FROM departments d
LEFT JOIN users u ON d.dept_id = u.dept_id
LEFT JOIN salary_history sh ON u.user_id = sh.user_id
WHERE d.budget IS NOT NULL
GROUP BY d.dept_name
HAVING COUNT(u.user_id) > 0
ORDER BY COUNT(u.user_id) DESC;
