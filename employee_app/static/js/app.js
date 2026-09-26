// ============================================================
// Employee Management System - Global App JavaScript
// Role-Based Navigation + Authentication
// ============================================================


// ------------------------------------------------------------
// Authentication helpers
// ------------------------------------------------------------

function getToken() {
    return localStorage.getItem("access_token");
}

function getUsername() {
    return localStorage.getItem("username") || "";
}

function getRole() {
    return localStorage.getItem("role") || "";
}


// ------------------------------------------------------------
// API helper
// ------------------------------------------------------------

async function apiFetch(url, options = {}) {
    const token = getToken();

    const headers = {
        ...(options.headers || {})
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    if (options.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    return fetch(url, {
        ...options,
        headers
    });
}


// ------------------------------------------------------------
// Login
// ------------------------------------------------------------

async function handleLogin(event) {
    event.preventDefault();

    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const message = document.getElementById("loginMessage");

    if (!usernameInput || !passwordInput) {
        return;
    }

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!username || !password) {
        if (message) {
            message.textContent = "Please enter username and password.";
        }
        return;
    }

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed");
        }

        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("username", data.user.username);
        localStorage.setItem("role", data.user.role);

        window.location.href = "/dashboard";

    } catch (error) {
        if (message) {
            message.textContent = error.message;
        }
    }
}


// ------------------------------------------------------------
// Logout
// ------------------------------------------------------------

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");

    window.location.href = "/";
}


// ------------------------------------------------------------
// Role-based sidebar
// ------------------------------------------------------------

function configureSidebar() {
    const sidebar = document.querySelector(".sidebar");

    if (!sidebar) {
        return;
    }

    const role = getRole();
    const username = getUsername();

    let navigation = "";

    // --------------------------------------------------------
    // ADMIN
    // --------------------------------------------------------

   if (role === "admin") {

    navigation = `
    <a href="/dashboard">
        Dashboard
    </a>

    <a href="/employees-page">
        Employees
    </a>

    <a href="/departments-page">
        Departments
    </a>

    <a href="/attendance-page">
        Attendance
    </a>

    <a href="/payroll-page">
        Payroll
    </a>

    <a href="/users-page">
        User Management
    </a>

    <a href="/profile-page">
        My Profile
    </a>
`;
}

    // --------------------------------------------------------
    // HR
    // --------------------------------------------------------

    else if (role === "hr") {

       navigation = `
    <a href="/dashboard">
        Dashboard
    </a>

    <a href="/employees-page">
        Employees
    </a>

    <a href="/departments-page">
        Departments
    </a>

    <a href="/attendance-page">
        Attendance
    </a>

    <a href="/payroll-page">
        Payroll
    </a>
`;
    }


    // --------------------------------------------------------
    // No valid role
    // --------------------------------------------------------

    else {

        navigation = `
            <a href="/">
                Login
            </a>

            <a href="/register">
                Register
            </a>
        `;
    }


    // Keep the Employee System heading,
    // replace only the navigation area.

    const existingNav = sidebar.querySelector("nav");

    if (existingNav) {
    existingNav.innerHTML = navigation;
} else {
    const nav = document.createElement("nav");
    nav.innerHTML = navigation;
    sidebar.appendChild(nav);
}


// ------------------------------------------------------------
// Red Logout button
// ------------------------------------------------------------

let logoutButton = sidebar.querySelector(".sidebar-logout");

if (!logoutButton) {

    logoutButton = document.createElement("a");

    logoutButton.href = "#";
    logoutButton.className = "sidebar-logout";
    logoutButton.textContent = "Logout";

    logoutButton.addEventListener("click", function (event) {
        event.preventDefault();
        logout();
    });

    sidebar.appendChild(logoutButton);
}

    // --------------------------------------------------------
    // Update welcome text
    // --------------------------------------------------------

    const welcomeElements = document.querySelectorAll(
        "[data-current-user]"
    );

    welcomeElements.forEach(element => {
        element.textContent = username;
    });


    // --------------------------------------------------------
    // Update role badge
    // --------------------------------------------------------

    const roleElements = document.querySelectorAll(
        "[data-current-role]"
    );

    roleElements.forEach(element => {
        element.textContent = role.toUpperCase();
    });
}


// ------------------------------------------------------------
// Dashboard loading
// ------------------------------------------------------------

async function loadDashboard() {

    const role = getRole();
    const username = getUsername();

    if (!role || !getToken()) {
        window.location.href = "/";
        return;
    }

    const usernameElements = document.querySelectorAll(
        "[data-current-user]"
    );

    usernameElements.forEach(element => {
        element.textContent = username;
    });

    const roleElements = document.querySelectorAll(
        "[data-current-role]"
    );

    roleElements.forEach(element => {
        element.textContent = role.toUpperCase();
    });


    try {

        let endpoint = "";

        if (role === "admin") {
            endpoint = "/dashboard/admin";
        }

        else if (role === "hr") {
            endpoint = "/dashboard/hr";
        }

        else if (role === "employee") {
            endpoint = "/dashboard/me";
        }

        else {
            throw new Error("Invalid user role");
        }


        const response = await apiFetch(endpoint);

        if (!response.ok) {

            if (response.status === 401) {
                logout();
                return;
            }

            const errorData = await response.json();
            throw new Error(
                errorData.detail || "Unable to load dashboard"
            );
        }


        const data = await response.json();

        // Hide all dashboard sections first.

        const adminDashboard =
            document.getElementById("adminDashboard");

        const hrDashboard =
            document.getElementById("hrDashboard");

        const employeeDashboard =
            document.getElementById("employeeDashboard");

        if (adminDashboard) {
            adminDashboard.style.display = "none";
        }

        if (hrDashboard) {
            hrDashboard.style.display = "none";
        }

        if (employeeDashboard) {
            employeeDashboard.style.display = "none";
        }


        // Show correct dashboard.

        if (role === "admin" && adminDashboard) {

            adminDashboard.style.display = "block";

            const dashboard = data.dashboard;

            setText("totalEmployees", dashboard.total_employees);
            setText("activeEmployees", dashboard.active_employees);
            setText("totalDepartments", dashboard.total_departments);

            setText(
                "presentToday",
                dashboard.attendance_today.present
            );

            setText(
                "absentToday",
                dashboard.attendance_today.absent
            );

            setText(
                "leaveToday",
                dashboard.attendance_today.leave
            );

            setText(
                "salaryRecords",
                dashboard.total_salary_records
            );

            setText(
                "totalPayroll",
                formatCurrency(dashboard.total_payroll)
            );
        }


        else if (role === "hr" && hrDashboard) {

            hrDashboard.style.display = "block";

            const dashboard = data.dashboard;

            setText("hrTotalEmployees", dashboard.total_employees);
            setText("hrActiveEmployees", dashboard.active_employees);
            setText("hrTotalDepartments", dashboard.total_departments);

            setText(
                "hrPresentToday",
                dashboard.attendance_today.present
            );

            setText(
                "hrAbsentToday",
                dashboard.attendance_today.absent
            );

            setText(
                "hrLeaveToday",
                dashboard.attendance_today.leave
            );

            setText(
                "hrSalaryRecords",
                dashboard.total_salary_records
            );
        }


        else if (role === "employee" && employeeDashboard) {

            employeeDashboard.style.display = "block";

            const employee = data.employee;

            setText(
                "employeeId",
                employee.employee_id
            );

            setText(
                "employeeName",
                employee.name
            );

            setText(
                "employeeEmail",
                employee.email
            );

            setText(
                "employeeDesignation",
                employee.designation
            );

            setText(
                "employeeDepartment",
                employee.department_id
            );

            setText(
                "employeeStatus",
                employee.employment_status
            );


            if (data.today_attendance) {

                setText(
                    "todayAttendance",
                    data.today_attendance.status
                );

            } else {

                setText(
                    "todayAttendance",
                    "Not marked"
                );
            }


            if (data.salary) {

                setText(
                    "employeeNetSalary",
                    formatCurrency(data.salary.net_salary)
                );

            } else {

                setText(
                    "employeeNetSalary",
                    "Not available"
                );
            }
        }


    } catch (error) {

        console.error("Dashboard error:", error);

        const errorElement =
            document.getElementById("dashboardError");

        if (errorElement) {
            errorElement.textContent = error.message;
            errorElement.style.display = "block";
        }
    }
}


// ------------------------------------------------------------
// Utility functions
// ------------------------------------------------------------

function setText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value ?? "";
    }
}


function formatCurrency(value) {

    if (value === null || value === undefined) {
        return "₹0";
    }

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
    }).format(value);
}


// ------------------------------------------------------------
// Page initialization
// ------------------------------------------------------------

document.addEventListener("DOMContentLoaded", function () {

    const token = getToken();

    // Configure role-based sidebar on EVERY page.
    configureSidebar();


    // Login page
    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }


    // Dashboard page
    if (
        document.getElementById("adminDashboard") ||
        document.getElementById("hrDashboard") ||
        document.getElementById("employeeDashboard")
    ) {
        if (!token) {
            window.location.href = "/";
            return;
        }

        loadDashboard();
    }
});