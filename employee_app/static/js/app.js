
// ============================================================
// GLOBAL AUTHENTICATION HELPERS
// ============================================================

function getToken() {
    return localStorage.getItem("access_token");
}

function getUsername() {
    return localStorage.getItem("username") || "";
}

function getRole() {
    return localStorage.getItem("role") || "";
}

async function apiFetch(url, options = {}) {
    const headers = {
        ...(options.headers || {})
    };

    const token = getToken();

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


// ============================================================
// LOGIN
// ============================================================

async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById("username")?.value.trim();
    const password = document.getElementById("password")?.value;
    const message = document.getElementById("loginMessage");

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
                username,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed.");
        }

        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("username", data.user.username);
        localStorage.setItem("role", data.user.role);

        window.location.href = "/dashboard";

    } catch (error) {
        if (message) {
            message.textContent = error.message || "Login failed.";
        }
    }
}


// ============================================================
// LOGOUT
// ============================================================

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");

    window.location.href = "/";
}


// ============================================================
// ROLE-BASED SIDEBAR
// ============================================================

function configureSidebar() {
    const sidebar = document.querySelector(".sidebar");

    if (!sidebar) {
        return;
    }

    const role = getRole();
    const username = getUsername();

    let navigation = "";

    if (role === "admin") {
        navigation = `
            <a href="/dashboard">Dashboard</a>
            <a href="/employees-page">Employees</a>
            <a href="/departments-page">Departments</a>
            <a href="/attendance-page">Attendance</a>
            <a href="/payroll-page">Payroll</a>
            <a href="/users-page">User Management</a>
        `;

    } else if (role === "hr") {
        navigation = `
            <a href="/dashboard">Dashboard</a>
            <a href="/employees-page">Employees</a>
            <a href="/attendance-page">Attendance</a>
            <a href="/payroll-page">Payroll</a>
            
        `;

    } else if (role === "employee") {
        navigation = `
            <a href="/dashboard">Dashboard</a>
            <a href="/attendance-page">My Attendance</a>
            <a href="/payroll-page">My Salary</a>
            <a href="/profile-page">My Profile</a>
        `;

    } else {
        navigation = `
            <a href="/">Login</a>
            <a href="/register">Register</a>
        `;
    }

    // Create or update navigation.
    let nav = sidebar.querySelector("nav");

    if (!nav) {
        nav = document.createElement("nav");
        sidebar.appendChild(nav);
    }

    nav.innerHTML = navigation;

    // Highlight the current page.
    const currentPath = window.location.pathname;

    nav.querySelectorAll("a").forEach((link) => {
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });

    // Remove all old logout links and buttons.
    sidebar.querySelectorAll("a, button").forEach((element) => {
        const text = element.textContent.trim().toLowerCase();

        if (
            text === "logout" ||
            element.id === "logoutButton" ||
            element.classList.contains("sidebar-logout")
        ) {
            element.remove();
        }
    });

    // Create exactly ONE logout button.
    const logoutButton = document.createElement("button");

    logoutButton.type = "button";
    logoutButton.id = "logoutButton";
    logoutButton.className = "logout-button";
    logoutButton.textContent = "Logout";

    logoutButton.addEventListener("click", logout);

    sidebar.appendChild(logoutButton);

    // Update username.
    document.querySelectorAll("[data-current-user]").forEach((element) => {
        element.textContent = username || "User";
    });

    // Update role badge.
    document.querySelectorAll("[data-current-role]").forEach((element) => {
        element.textContent = role ? role.toUpperCase() : "-";
    });
}


// ============================================================
// DASHBOARD HELPERS
// ============================================================

function setText(id, value) {
    const element = document.getElementById(id);

    if (!element) {
        return;
    }

    element.textContent =
        value === null || value === undefined
            ? "-"
            : value;
}

function formatCurrency(value) {
    const amount = Number(value ?? 0);

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
    }).format(Number.isFinite(amount) ? amount : 0);
}


// ============================================================
// LOAD ROLE-SPECIFIC DASHBOARD
// ============================================================

async function loadDashboard() {
    const role = getRole();

    if (!getToken() || !role) {
        window.location.href = "/";
        return;
    }

    const adminDashboard = document.getElementById("adminDashboard");
    const hrDashboard = document.getElementById("hrDashboard");
    const employeeDashboard = document.getElementById("employeeDashboard");

    // Hide all dashboard sections first.
    [adminDashboard, hrDashboard, employeeDashboard].forEach((section) => {
        if (section) {
            section.style.display = "none";
        }
    });

    let endpoint = "";

    if (role === "admin") {
        endpoint = "/dashboard/admin";
    } else if (role === "hr") {
        endpoint = "/dashboard/hr";
    } else if (role === "employee") {
        endpoint = "/dashboard/me";
    } else {
        window.location.href = "/";
        return;
    }

    setText("dashboardRole", role.toUpperCase());
    setText("welcomeMessage", `Welcome, ${getUsername()}`);

    try {
        const response = await apiFetch(endpoint);

        if (response.status === 401) {
            logout();
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));

            throw new Error(
                errorData.detail || "Unable to load dashboard."
            );
        }

        const data = await response.json();

        // ----------------------------------------------------
        // ADMIN DASHBOARD
        // ----------------------------------------------------

        if (role === "admin" && adminDashboard) {
            adminDashboard.style.display = "block";

            const dashboard = data.dashboard || {};
            const attendance = dashboard.attendance_today || {};

            setText("totalEmployees", dashboard.total_employees ?? 0);
            setText("activeEmployees", dashboard.active_employees ?? 0);
            setText("totalDepartments", dashboard.total_departments ?? 0);

            setText("presentToday", attendance.present ?? 0);
            setText("absentToday", attendance.absent ?? 0);
            setText("leaveToday", attendance.leave ?? 0);

            // Support both IDs used in dashboard versions.
            setText("salaryRecords", dashboard.total_salary_records ?? 0);
            setText("totalSalaryRecords", dashboard.total_salary_records ?? 0);

            setText(
                "totalPayroll",
                formatCurrency(dashboard.total_payroll ?? 0)
            );
        }

        // ----------------------------------------------------
        // HR DASHBOARD
        // ----------------------------------------------------

        if (role === "hr" && hrDashboard) {
            hrDashboard.style.display = "block";

            const dashboard = data.dashboard || {};
            const attendance = dashboard.attendance_today || {};

            setText("hrTotalEmployees", dashboard.total_employees ?? 0);
            setText("hrActiveEmployees", dashboard.active_employees ?? 0);
            setText("hrTotalDepartments", dashboard.total_departments ?? 0);

            setText("hrPresentToday", attendance.present ?? 0);
            setText("hrAbsentToday", attendance.absent ?? 0);
            setText("hrLeaveToday", attendance.leave ?? 0);

            setText("hrSalaryRecords", dashboard.total_salary_records ?? 0);
        }

        // ----------------------------------------------------
        // EMPLOYEE DASHBOARD
        // ----------------------------------------------------

        if (role === "employee" && employeeDashboard) {
            employeeDashboard.style.display = "block";

            const employee = data.employee || {};

            setText("employeeId", employee.employee_id);
            setText("employeeName", employee.name);
            setText("employeeEmail", employee.email);
            setText("employeeDesignation", employee.designation);
            setText("employeeDepartment", employee.department_id);
            setText("employeeStatus", employee.employment_status);

            const attendanceStatus =
                data.today_attendance?.status || "Not marked";

            setText("todayAttendance", attendanceStatus);
            setText("employeeAttendanceStatus", attendanceStatus);

            const netSalary = data.salary?.net_salary;

            setText(
                "employeeNetSalary",
                netSalary == null ? "Not available" : formatCurrency(netSalary)
            );
        }

    } catch (error) {
        console.error("Dashboard error:", error);

        const errorElement = document.getElementById("dashboardError");

        if (errorElement) {
            errorElement.textContent =
                error.message || "Unable to load dashboard.";

            errorElement.style.display = "block";
        }
    }
}


// ============================================================
// PAGE INITIALIZATION
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
    configureSidebar();

    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }

    const isDashboardPage =
        document.getElementById("adminDashboard") ||
        document.getElementById("hrDashboard") ||
        document.getElementById("employeeDashboard");

    if (isDashboardPage) {
        loadDashboard();
    }
});