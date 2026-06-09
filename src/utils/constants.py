"""Constants and fallback data for the AI pipeline."""

EXECUTIVE_DASHBOARD_QUERIES = [
    {
        "name": "Headcount by Plant",
        "sql": "SELECT PlantName, COUNT(GlobalUserId) AS Headcount FROM employee_master GROUP BY PlantName;"
    },
    {
        "name": "Gender Diversity",
        "sql": "SELECT Gender, COUNT(GlobalUserId) AS Count FROM employee_master GROUP BY Gender;"
    },
    {
        "name": "Recent Attrition",
        "sql": "SELECT strftime('%Y-%m', EmployeeJobEndDate) AS Month, COUNT(GlobalUserId) AS Leavers FROM employee_master WHERE EmployeeStatus = 'Terminated' AND EmployeeJobEndDate >= date('now', '-6 months') GROUP BY Month;"
    }
]