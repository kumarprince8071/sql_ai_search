### EXAMPLES ###
Study these examples to understand how to apply the filters and return the required JSON array format.

USER QUERY: "show current headcount in smr Australia"
RESOLVED FILTERS: 
{
  "company_name": "employee_master.CompanyName LIKE '%smr Australia%'",
  "status": "employee_master.EmployeeStatus LIKE 'Active'"
}
OUTPUT:
[
  {
    "sql": "SELECT COUNT(GlobalUserId) AS CurrentHeadcount FROM employee_master WHERE CompanyName LIKE '%smr Australia%' AND EmployeeStatus LIKE 'Active';"
  }
]

USER QUERY: "Show me the details of unauthorized long absenteeism"
RESOLVED FILTERS: 
{
  "status": "employee_inouttime.AttendanceStatus LIKE 'Absent'"
}
OUTPUT:
[
  {
    "sql": "SELECT emp.FullName, inout.AttendanceDate FROM employee_master emp JOIN employee_inouttime inout ON emp.GlobalUserId = inout.GlobalUserID WHERE inout.AttendanceStatus LIKE 'Absent' AND NOT EXISTS (SELECT 1 FROM employee_leavetaken lt WHERE lt.GlobalUserId = emp.GlobalUserId AND lt.LeaveDate = inout.AttendanceDate);"
  }
]

USER QUERY: "Show the month wise absent ratio of  employees in last year"
RESOLVED FILTERS: 
{
  "manager_id": "manager_master.ManagerId = ''",
  "date": "employee_inouttime.AttendanceDate >= date('now', '-1 year')"
}
OUTPUT:
[
  {
    "sql": "SELECT strftime('%Y-%m', inout.AttendanceDate) AS Month, SUM(CASE WHEN inout.AttendanceStatus LIKE 'Absent' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS AbsentRatioPercentage FROM manager_master mm JOIN employee_inouttime inout ON mm.ReporteeID = inout.GlobalUserID WHERE mm.ManagerId = '{GlobalUserID}' AND inout.AttendanceDate >= date('now', '-1 year') GROUP BY Month ORDER BY Month;"
  }
]

USER QUERY: "Show the trend of average working hours of white collar employees of Noida plant in last 6 months"
RESOLVED FILTERS: 
{
  "collar_type": "employee_master.CollarType LIKE 'White Collar'",
  "plant_name": "employee_master.PlantName LIKE '%Noida%'",
  "date": "employee_inouttime.AttendanceDate >= date('now', '-6 months')"
}
OUTPUT:
[
  {
    "sql": "SELECT strftime('%Y-%m', inout.AttendanceDate) AS Month, AVG(CAST(substr(inout.TotalAttendedHours_HHMM, 1, 2) AS FLOAT) + CAST(substr(inout.TotalAttendedHours_HHMM, 4, 2) AS FLOAT) / 60.0) AS AvgHours FROM employee_master emp JOIN employee_inouttime inout ON emp.GlobalUserId = inout.GlobalUserID WHERE emp.CollarType LIKE 'White Collar' AND emp.PlantName LIKE '%Noida%' AND inout.AttendanceDate >= date('now', '-6 months') GROUP BY Month ORDER BY Month;"
  }
]

USER QUERY: "Show me the month wise leave count of my reportees in last 6 months"
RESOLVED FILTERS: 
{
  "manager_id": "manager_master.ManagerId = '{GlobalUserID}'",
  "date": "employee_leavetaken.LeaveDate >= date('now', '-6 months')"
}
OUTPUT:
[
  {
    "sql": "SELECT strftime('%Y-%m', lt.LeaveDate) AS Month, COUNT(lt.LeaveDate) AS LeaveCount FROM manager_master mm JOIN employee_leavetaken lt ON mm.ReporteeID = lt.GlobalUserId WHERE mm.ManagerId = '{GlobalUserID}' AND lt.LeaveDate >= date('now', '-6 months') GROUP BY Month ORDER BY Month;"
  }
]

USER QUERY: "Show the list of people having more than 40 years of experience with date of joining detail"
RESOLVED FILTERS: 
{
  "experience": "employee_master.Tenure > 40"
}
OUTPUT:
[
  {
    "sql": "SELECT FullName, EmployeeJobStartDate, Tenure FROM employee_master WHERE Tenure > 40;"
  }
]

USER QUERY: "Show the plant wise count of employees joined in last month"
RESOLVED FILTERS: 
{
  "date": "employee_master.EmployeeJobStartDate >= date('now', 'start of month', '-1 month') AND employee_master.EmployeeJobStartDate < date('now', 'start of month')"
}
OUTPUT:
[
  {
    "sql": "SELECT PlantName, COUNT(GlobalUserId) AS EmployeeCount FROM employee_master WHERE EmployeeJobStartDate >= date('now', 'start of month', '-1 month') AND EmployeeJobStartDate < date('now', 'start of month') GROUP BY PlantName;"
  }
]

USER QUERY: "Show the list of employees joined in Brazil last month"
RESOLVED FILTERS: 
{
  "country": "employee_master.Country LIKE 'Brazil'",
  "date": "employee_master.EmployeeJobStartDate >= date('now', 'start of month', '-1 month') AND employee_master.EmployeeJobStartDate < date('now', 'start of month')"
}
OUTPUT:
[
  {
    "sql": "SELECT FullName, EmployeeJobStartDate FROM employee_master WHERE Country LIKE 'Brazil' AND EmployeeJobStartDate >= date('now', 'start of month', '-1 month') AND EmployeeJobStartDate < date('now', 'start of month');"
  }
]

USER QUERY: "Show the employee count and gender diversity percentage for Hungary and India."
RESOLVED FILTERS: 
{
  "country": "(employee_master.Country LIKE 'Hungary' OR employee_master.Country LIKE 'India')"
}
OUTPUT:
[
  {
    "sql": "SELECT Country, Gender, COUNT(GlobalUserId) AS EmpCount, COUNT(GlobalUserId) * 100.0 / SUM(COUNT(GlobalUserId)) OVER(PARTITION BY Country) AS GenderPercentage FROM employee_master WHERE (Country LIKE 'Hungary' OR Country LIKE 'India') GROUP BY Country, Gender;"
  }
]

USER QUERY: "show the leave balance of Som Dutt Mehta"
RESOLVED FILTERS: 
{
  "employee": "employee_master.FullName LIKE 'Som Dutt Mehta'"
}
OUTPUT:
[
  {
    "sql": "SELECT lb.* FROM employee_leavebalance lb JOIN employee_master emp ON lb.GlobalUserId = emp.GlobalUserId WHERE emp.FullName LIKE 'Som Dutt Mehta';"
  }
]

USER QUERY: "Show my leave balance."
RESOLVED FILTERS: 
{
  "employee": "employee_leavebalance.GlobalUserId = "" "
}
OUTPUT:
[
  {
    "sql": "SELECT * FROM employee_leavebalance WHERE GlobalUserId = '{GlobalUserID}';"
  }
]

USER QUERY: "Show me the collar wise employee count across plants"
RESOLVED FILTERS: {}
OUTPUT:
[
  {
    "sql": "SELECT PlantName, CollarType, COUNT(GlobalUserId) AS EmployeeCount FROM employee_master GROUP BY PlantName, CollarType;"
  }
]

USER QUERY: "List of all employees who on average in last 3 months are attending less than 10 Hours"
RESOLVED FILTERS: 
{
  "date": "employee_inouttime.AttendanceDate >= date('now', '-3 months')"
}
OUTPUT:
[
  {
    "sql": "SELECT emp.FullName, AVG(CAST(substr(inout.TotalAttendedHours_HHMM, 1, 2) AS FLOAT)) AS AvgHours FROM employee_master emp JOIN employee_inouttime inout ON emp.GlobalUserId = inout.GlobalUserID WHERE inout.AttendanceDate >= date('now', '-3 months') GROUP BY emp.GlobalUserId, emp.FullName HAVING AvgHours < 10;"
  }
]

USER QUERY: "Show the site wise list of employees who left the company in last month."
RESOLVED FILTERS: 
{
  "status": "employee_master.EmployeeStatus LIKE 'Inactive'",
  "date": "employee_master.EmployeeJobEndDate >= date('now', 'start of month', '-1 month') AND employee_master.EmployeeJobEndDate < date('now', 'start of month')"
}
OUTPUT:
[
  {
    "sql": "SELECT Location, FullName, EmployeeJobEndDate FROM employee_master WHERE EmployeeStatus LIKE 'Inactive' AND EmployeeJobEndDate >= date('now', 'start of month', '-1 month') AND EmployeeJobEndDate < date('now', 'start of month') ORDER BY Location;"
  }
]

USER QUERY: "show the leaves taken by som dutt in last 6 months"
RESOLVED FILTERS: 
{
  "employee": "employee_master.FullName LIKE '%som dutt%'",
  "date": "employee_leavetaken.LeaveDate >= date('now', '-6 months')"
}
OUTPUT:
[
  {
    "sql": "SELECT lt.LeaveDate, lt.LeaveTypeName, lt.LeaveUnitsTaken, lt.ApprovalStatus FROM employee_leavetaken lt JOIN employee_master emp ON lt.GlobalUserId = emp.GlobalUserId WHERE emp.FullName LIKE '%som dutt%' AND lt.LeaveDate >= date('now', '-6 months');"
  }
]

USER QUERY: "Show my OD in last month"
RESOLVED FILTERS: 
{
  "employee": "employee_inouttime.GlobalUserID = '{GlobalUserID}'",
  "attendance_type": "employee_inouttime.AttendanceType LIKE 'OD'",
  "date": "employee_inouttime.AttendanceDate >= date('now', 'start of month', '-1 month')"
}
OUTPUT:
[
  {
    "sql": "SELECT AttendanceDate, PunchInTime, PunchOutTime FROM employee_inouttime WHERE GlobalUserID = '{GlobalUserID}' AND AttendanceType LIKE 'OD' AND AttendanceDate >= date('now', 'start of month', '-1 month');"
  }
]

USER QUERY: "show the bank account number Andrea Whitford"
RESOLVED FILTERS: 
{
  "employee": "employee_master.FullName LIKE 'Andrea Whitford'"
}
OUTPUT:
[
  {
    "sql": "SELECT AccountNumber, BankAccountOwnerName FROM employee_master WHERE FullName LIKE 'Andrea Whitford';"
  }
]

USER QUERY: "show the direct reportees of Tarun Kumar Sharma"
RESOLVED FILTERS: 
{
  "manager": "employee_master.FullName LIKE 'Tarun Kumar Sharma'"
}
OUTPUT:
[
  {
    "sql": "SELECT emp.FullName AS ReporteeName, emp.JobTitle FROM manager_master mm JOIN employee_master mgr ON mm.ManagerId = mgr.GlobalUserId JOIN employee_master emp ON mm.ReporteeID = emp.GlobalUserId WHERE mgr.FullName LIKE 'Tarun Kumar Sharma';"
  }
]

USER QUERY: "what was the attendance of sudha kumari in March 2026"
RESOLVED FILTERS: 
{
  "employee": "employee_master.FullName LIKE 'sudha kumari'",
  "start_date": "employee_inouttime.AttendanceDate >= '2026-03-01'",
  "end_date": "employee_inouttime.AttendanceDate <= '2026-03-31'"
}
OUTPUT:
[
  {
    "sql": "SELECT inout.AttendanceDate, inout.PunchInTime, inout.PunchOutTime, inout.AttendanceStatus FROM employee_inouttime inout JOIN employee_master emp ON inout.GlobalUserID = emp.GlobalUserId WHERE emp.FullName LIKE 'sudha kumari' AND inout.AttendanceDate >= '2026-03-01' AND inout.AttendanceDate <= '2026-03-31';"
  }
]

USER QUERY: "What is the distribution of leave approval status for all leaves processed in the last month, grouped by the type of leaves?"
RESOLVED FILTERS: 
{
  "date": "employee_leavetaken.LeaveDate >= date('now', 'start of month', '-1 month')"
}
OUTPUT:
[
  {
    "sql": "SELECT LeaveTypeName, ApprovalStatus, COUNT(*) AS StatusCount FROM employee_leavetaken WHERE LeaveDate >= date('now', 'start of month', '-1 month') GROUP BY LeaveTypeName, ApprovalStatus;"
  }
]

USER QUERY: "List the names and departments of employees who have the earned leave left more than 50% in the last quarter."
RESOLVED FILTERS: 
{
  "math": "employee_leavebalance.EarnLeave_Left > (employee_leavebalance.EarnLeave_Entitled * 0.50)"
}
OUTPUT:
[
  {
    "sql": "SELECT emp.FullName, emp.Department, lb.EarnLeave_Left, lb.EarnLeave_Entitled FROM employee_master emp JOIN employee_leavebalance lb ON emp.GlobalUserId = lb.GlobalUserId WHERE lb.EarnLeave_Left > (lb.EarnLeave_Entitled * 0.50);"
  }
]

USER QUERY: "show me the name and department and manager name of all employee whose daily working hour is less than 9:15 hours"
RESOLVED FILTERS: 
{
  "time": "employee_inouttime.TotalAttendedHours_HHMM < '09:15'"
}
OUTPUT:
[
  {
    "sql": "SELECT emp.FullName, emp.Department, emp.ManagerName, inout.AttendanceDate, inout.TotalAttendedHours_HHMM FROM employee_master emp JOIN employee_inouttime inout ON emp.GlobalUserId = inout.GlobalUserID WHERE inout.TotalAttendedHours_HHMM < '09:15';"
  }
]

USER QUERY: "What is the total number of hours worked by the employees under tarun in last year month by month?"
RESOLVED FILTERS: 
{
  "manager": "employee_master.FullName LIKE '%tarun%'",
  "date": "employee_inouttime.AttendanceDate >= date('now', '-1 year')"
}
OUTPUT:
[
  {
    "sql": "SELECT strftime('%Y-%m', inout.AttendanceDate) AS Month, SUM(CAST(substr(inout.TotalAttendedHours_HHMM, 1, 2) AS FLOAT)) AS TotalHours FROM manager_master mm JOIN employee_master mgr ON mm.ManagerId = mgr.GlobalUserId JOIN employee_inouttime inout ON mm.ReporteeID = inout.GlobalUserID WHERE mgr.FullName LIKE '%tarun%' AND inout.AttendanceDate >= date('now', '-1 year') GROUP BY Month ORDER BY Month;"
  }
]

USER QUERY: "How many users have never requested a sick leave request and also have no late login attempts?"
RESOLVED FILTERS: 
{
  "leave_type": "employee_leavetaken.LeaveTypeCode = 'SL'",
  "status": "employee_inouttime.AttendanceStatus LIKE 'Late'"
}
OUTPUT:
[
  {
    "sql": "SELECT COUNT(emp.GlobalUserId) AS CompliantUserCount FROM employee_master emp WHERE NOT EXISTS (SELECT 1 FROM employee_leavetaken lt WHERE lt.GlobalUserId = emp.GlobalUserId AND lt.LeaveTypeCode = 'SL') AND NOT EXISTS (SELECT 1 FROM employee_inouttime inout WHERE inout.GlobalUserID = emp.GlobalUserId AND inout.AttendanceStatus LIKE 'Late');"
  }
]

USER QUERY: "Identify the top three departments by average employee attendance rate, considering only employees who have completed at least 10 years."
RESOLVED FILTERS: 
{
  "tenure": "employee_master.Tenure >= 10",
  "status": "employee_inouttime.AttendanceStatus LIKE 'Present'"
}

OUTPUT:
[
  {
    "sql": "SELECT emp.Department, COUNT(inout.Id) AS TotalPresentDays FROM employee_master emp JOIN employee_inouttime inout ON emp.GlobalUserId = inout.GlobalUserID WHERE emp.Tenure >= 10 AND inout.AttendanceStatus LIKE 'Present' GROUP BY emp.Department ORDER BY TotalPresentDays DESC LIMIT 3;"
  }
]