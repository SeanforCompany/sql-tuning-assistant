-- 튜닝이 필요한 샘플 쿼리들

-- 쿼리 1: 비효율적인 SELECT * 사용
SELECT * 
FROM users u 
JOIN departments d ON u.dept_id = d.dept_id 
WHERE u.user_name LIKE '%김%' 
ORDER BY u.hire_date;

-- 쿼리 2: GROUP BY와 집계 함수 사용
SELECT d.dept_name, COUNT(*) as user_count, AVG(u.salary) as avg_salary
FROM users u 
JOIN departments d ON u.dept_id = d.dept_id 
WHERE u.status = 'ACTIVE'
GROUP BY d.dept_name
HAVING COUNT(*) > 5
ORDER BY avg_salary DESC;

-- 쿼리 3: 서브쿼리가 있는 복잡한 쿼리  
SELECT u.user_name, u.salary, d.dept_name
FROM users u
JOIN departments d ON u.dept_id = d.dept_id
WHERE u.salary > (
    SELECT AVG(salary) 
    FROM users 
    WHERE dept_id = u.dept_id
)
AND u.user_id IN (
    SELECT user_id 
    FROM salary_history 
    WHERE change_date > ADD_MONTHS(SYSDATE, -12)
);

-- 쿼리 4: 다중 조인과 집계
SELECT d.dept_name, 
       COUNT(u.user_id) as total_users,
       SUM(u.salary) as total_salary,
       COUNT(sh.history_id) as salary_changes
FROM departments d
LEFT JOIN users u ON d.dept_id = u.dept_id
LEFT JOIN salary_history sh ON u.user_id = sh.user_id 
WHERE d.budget > 1000000
GROUP BY d.dept_name
