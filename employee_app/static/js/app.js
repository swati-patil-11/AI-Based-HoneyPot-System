// =========================================================
// LOGIN
// =========================================================

const loginForm = document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const username =
            document.getElementById("username").value;

        const password =
            document.getElementById("password").value;

        const message =
            document.getElementById("loginMessage");

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

                message.textContent =
                    data.detail || "Login failed.";

                return;
            }

            localStorage.setItem(
                "access_token",
                data.access_token
            );

            localStorage.setItem(
                "username",
                data.user.username
            );

            localStorage.setItem(
                "role",
                data.user.role
            );

            window.location.href = "/dashboard";

        } catch (error) {

            console.error(error);

            message.textContent =
                "Unable to connect to server.";

        }

    });

}


// =========================================================
// REGISTER
// =========================================================

const registerForm =
    document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();

            const username =
                document.getElementById(
                    "registerUsername"
                ).value;

            const email =
                document.getElementById(
                    "registerEmail"
                ).value;

            const password =
                document.getElementById(
                    "registerPassword"
                ).value;

            const message =
                document.getElementById(
                    "registerMessage"
                );

            try {

                const response =
                    await fetch(
                        "/auth/register",
                        {

                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                username: username,
                                email: email,
                                password: password
                            })

                        }
                    );

                const data =
                    await response.json();

                if (!response.ok) {

                    message.textContent =
                        data.detail ||
                        "Registration failed.";

                    return;
                }

                message.textContent =
                    "Registration successful. Redirecting to login...";

                setTimeout(function () {

                    window.location.href = "/";

                }, 1500);

            } catch (error) {

                console.error(error);

                message.textContent =
                    "Unable to connect to server.";

            }

        }
    );

}


// =========================================================
// DASHBOARD
// =========================================================

const dashboardPage =
    document.getElementById("adminDashboard");

if (dashboardPage) {

    const token =
        localStorage.getItem("access_token");

    const role =
        localStorage.getItem("role");

    const username =
        localStorage.getItem("username");

    if (!token) {

        window.location.href = "/";

    } else {

        const welcomeMessage =
            document.getElementById(
                "welcomeMessage"
            );

        if (welcomeMessage) {

            welcomeMessage.textContent =
                "Welcome, " + username;

        }

        if (role === "employee") {

            loadEmployeeDashboard(token);

        } else {

            loadAdminDashboard(token);

        }

    }

}


// =========================================================
// ADMIN DASHBOARD
// =========================================================

async function loadAdminDashboard(token) {

    const adminDashboard =
        document.getElementById(
            "adminDashboard"
        );

    const employeeDashboard =
        document.getElementById(
            "employeeDashboard"
        );

    if (adminDashboard) {

        adminDashboard.style.display =
            "block";

    }

    if (employeeDashboard) {

        employeeDashboard.style.display =
            "none";

    }

    try {

        const response =
            await fetch(
                "/dashboard/admin",
                {

                    headers: {
                        "Authorization":
                            "Bearer " + token
                    }

                }
            );

        if (!response.ok) {

            if (response.status === 401) {

                logout();

            }

            return;

        }

        const data =
            await response.json();

        const dashboard =
            data.dashboard;

        document.getElementById(
            "totalEmployees"
        ).textContent =
            dashboard.total_employees;

        document.getElementById(
            "activeEmployees"
        ).textContent =
            dashboard.active_employees;

        document.getElementById(
            "totalDepartments"
        ).textContent =
            dashboard.total_departments;

        document.getElementById(
            "presentToday"
        ).textContent =
            dashboard.attendance_today.present;

        document.getElementById(
            "absentToday"
        ).textContent =
            dashboard.attendance_today.absent;

        document.getElementById(
            "totalPayroll"
        ).textContent =
            "₹" +
            dashboard.total_payroll.toLocaleString();

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

    }

}


// =========================================================
// EMPLOYEE DASHBOARD
// =========================================================

async function loadEmployeeDashboard(token) {

    const adminDashboard =
        document.getElementById(
            "adminDashboard"
        );

    const employeeDashboard =
        document.getElementById(
            "employeeDashboard"
        );

    if (adminDashboard) {

        adminDashboard.style.display =
            "none";

    }

    if (employeeDashboard) {

        employeeDashboard.style.display =
            "block";

    }

    try {

        const response =
            await fetch(
                "/dashboard/me",
                {

                    headers: {
                        "Authorization":
                            "Bearer " + token
                    }

                }
            );

        if (!response.ok) {

            if (response.status === 401) {

                logout();

            }

            return;

        }

        const data =
            await response.json();

        const employee =
            data.employee;

        document.getElementById(
            "employeeId"
        ).textContent =
            employee.employee_id;

        document.getElementById(
            "employeeName"
        ).textContent =
            employee.name;

        document.getElementById(
            "employeeDesignation"
        ).textContent =
            employee.designation;

        document.getElementById(
            "employeeStatus"
        ).textContent =
            employee.employment_status;

        const attendance =
            data.today_attendance;

        if (attendance) {

            document.getElementById(
                "attendanceStatus"
            ).textContent =
                attendance.status +
                " - " +
                (attendance.remarks || "");

        } else {

            document.getElementById(
                "attendanceStatus"
            ).textContent =
                "No attendance recorded today.";

        }

        const salary =
            data.salary;

        if (salary) {

            document.getElementById(
                "basicSalary"
            ).textContent =
                "₹" +
                salary.basic_salary.toLocaleString();

            document.getElementById(
                "allowances"
            ).textContent =
                "₹" +
                salary.allowances.toLocaleString();

            document.getElementById(
                "deductions"
            ).textContent =
                "₹" +
                salary.deductions.toLocaleString();

            document.getElementById(
                "netSalary"
            ).textContent =
                "₹" +
                salary.net_salary.toLocaleString();

        }

    } catch (error) {

        console.error(
            "Employee dashboard error:",
            error
        );

    }

}


// =========================================================
// EMPLOYEE MANAGEMENT
// =========================================================

const employeeTableBody =
    document.getElementById(
        "employeeTableBody"
    );

if (employeeTableBody) {

    initializeEmployeePage();

}


function initializeEmployeePage() {

    const token =
        localStorage.getItem("access_token");

    const role =
        localStorage.getItem("role");

    const username =
        localStorage.getItem("username");

    if (!token) {

        window.location.href = "/";

        return;

    }

    const welcome =
        document.getElementById(
            "employeePageWelcome"
        );

    if (welcome) {

        welcome.textContent =
            "Welcome, " +
            username +
            " (" +
            role +
            ")";

    }

    const addButton =
        document.getElementById(
            "showAddEmployeeButton"
        );

    const addSection =
        document.getElementById(
            "addEmployeeSection"
        );

    if (role === "admin" || role === "hr") {

        if (addButton) {

            addButton.style.display =
                "block";

        }

        loadEmployees(token);

    } else {

        if (addButton) {

            addButton.style.display =
                "none";

        }

        const accessMessage =
            document.getElementById(
                "employeeAccessMessage"
            );

        if (accessMessage) {

            accessMessage.textContent =
                "You do not have permission to view employee management.";

        }

        employeeTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-table">
                    Access denied.
                </td>
            </tr>
        `;

    }

    if (addButton) {

        addButton.addEventListener(
            "click",
            function () {

                addSection.style.display =
                    "block";

                addButton.style.display =
                    "none";

            }
        );

    }

    const cancelButton =
        document.getElementById(
            "cancelEmployeeButton"
        );

    if (cancelButton) {

        cancelButton.addEventListener(
            "click",
            function () {

                addSection.style.display =
                    "none";

                if (
                    role === "admin" ||
                    role === "hr"
                ) {

                    addButton.style.display =
                        "block";

                }

            }
        );

    }

    const refreshButton =
        document.getElementById(
            "refreshEmployeesButton"
        );

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            function () {

                loadEmployees(token);

            }
        );

    }

    const employeeForm =
        document.getElementById(
            "employeeForm"
        );

    if (employeeForm) {

        employeeForm.addEventListener(
            "submit",
            createEmployee
        );

    }

}


async function loadEmployees(token) {

    employeeTableBody.innerHTML = `
        <tr>
            <td colspan="8" class="empty-table">
                Loading employees...
            </td>
        </tr>
    `;

    try {

        const response =
            await fetch(
                "/employees/",
                {

                    headers: {
                        "Authorization":
                            "Bearer " + token
                    }

                }
            );

        if (response.status === 401) {

            logout();

            return;

        }

        if (response.status === 403) {

            employeeTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-table">
                        Access denied.
                    </td>
                </tr>
            `;

            return;

        }

        if (!response.ok) {

            employeeTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-table">
                        Unable to load employees.
                    </td>
                </tr>
            `;

            return;

        }

        const employees =
            await response.json();

        employeeTableBody.innerHTML = "";

        if (employees.length === 0) {

            employeeTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-table">
                        No employees found.
                    </td>
                </tr>
            `;

            return;

        }

        employees.forEach(function (employee) {

            const row =
                document.createElement("tr");

            row.innerHTML = `

                <td>${employee.id}</td>

                <td>${employee.employee_id}</td>

                <td>
                    ${employee.first_name}
                    ${employee.last_name}
                </td>

                <td>${employee.email}</td>

                <td>${employee.department_id}</td>

                <td>${employee.designation}</td>

                <td>
                    <span class="status-badge">
                        ${employee.employment_status}
                    </span>
                </td>

                <td>

                    <button
                        class="delete-button"
                        onclick="deleteEmployee(${employee.id})"
                    >
                        Delete
                    </button>

                </td>

            `;

            employeeTableBody.appendChild(row);

        });

    } catch (error) {

        console.error(
            "Employee loading error:",
            error
        );

        employeeTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-table">
                    Unable to connect to server.
                </td>
            </tr>
        `;

    }

}


async function createEmployee(event) {

    event.preventDefault();

    const token =
        localStorage.getItem(
            "access_token"
        );

    const message =
        document.getElementById(
            "employeeFormMessage"
        );

    const employeeData = {

        employee_id:
            document.getElementById(
                "employeeId"
            ).value,

        first_name:
            document.getElementById(
                "firstName"
            ).value,

        last_name:
            document.getElementById(
                "lastName"
            ).value,

        email:
            document.getElementById(
                "email"
            ).value,

        phone:
            document.getElementById(
                "phone"
            ).value || null,

        department_id:
            Number(
                document.getElementById(
                    "departmentId"
                ).value
            ),

        designation:
            document.getElementById(
                "designation"
            ).value,

        joining_date:
            document.getElementById(
                "joiningDate"
            ).value,

        employment_status:
            document.getElementById(
                "employmentStatus"
            ).value

    };

    try {

        const response =
            await fetch(
                "/employees/",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json",

                        "Authorization":
                            "Bearer " + token

                    },

                    body:
                        JSON.stringify(
                            employeeData
                        )

                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            message.textContent =
                data.detail ||
                "Employee creation failed.";

            return;

        }

        message.textContent =
            "Employee created successfully.";

        document.getElementById(
            "employeeForm"
        ).reset();

        loadEmployees(token);

        setTimeout(function () {

            document.getElementById(
                "addEmployeeSection"
            ).style.display =
                "none";

            document.getElementById(
                "showAddEmployeeButton"
            ).style.display =
                "block";

            message.textContent = "";

        }, 1000);

    } catch (error) {

        console.error(error);

        message.textContent =
            "Unable to connect to server.";

    }

}


async function deleteEmployee(employeeId) {

    const token =
        localStorage.getItem(
            "access_token"
        );

    const confirmed =
        confirm(
            "Are you sure you want to delete this employee?"
        );

    if (!confirmed) {

        return;

    }

    try {

        const response =
            await fetch(
                "/employees/" + employeeId,
                {

                    method: "DELETE",

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            alert(
                data.detail ||
                "Unable to delete employee."
            );

            return;

        }

        alert(
            "Employee deleted successfully."
        );

        loadEmployees(token);

    } catch (error) {

        console.error(error);

        alert(
            "Unable to connect to server."
        );

    }

}


// =========================================================
// DEPARTMENT MANAGEMENT
// =========================================================

const departmentTableBody =
    document.getElementById(
        "departmentTableBody"
    );

if (departmentTableBody) {

    initializeDepartmentPage();

}


function initializeDepartmentPage() {

    const token =
        localStorage.getItem(
            "access_token"
        );

    const role =
        localStorage.getItem(
            "role"
        );

    const username =
        localStorage.getItem(
            "username"
        );


    if (!token) {

        window.location.href = "/";

        return;

    }


    const welcome =
        document.getElementById(
            "departmentPageWelcome"
        );


    if (welcome) {

        welcome.textContent =
            "Welcome, " +
            username +
            " (" +
            role +
            ")";

    }


    const addButton =
        document.getElementById(
            "showAddDepartmentButton"
        );


    const formSection =
        document.getElementById(
            "departmentFormSection"
        );


    if (role === "admin") {

        if (addButton) {

            addButton.style.display =
                "block";

        }

    } else {

        if (addButton) {

            addButton.style.display =
                "none";

        }

        const accessMessage =
            document.getElementById(
                "departmentAccessMessage"
            );


        if (accessMessage) {

            accessMessage.textContent =
                "Only administrators can add, edit, or delete departments.";

        }

    }


    loadDepartments(token, role);


    if (addButton) {

        addButton.addEventListener(
            "click",
            function () {

                openDepartmentCreateForm();

            }
        );

    }


    const cancelButton =
        document.getElementById(
            "cancelDepartmentButton"
        );


    if (cancelButton) {

        cancelButton.addEventListener(
            "click",
            function () {

                closeDepartmentForm();

            }
        );

    }


    const refreshButton =
        document.getElementById(
            "refreshDepartmentsButton"
        );


    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            function () {

                loadDepartments(
                    token,
                    role
                );

            }
        );

    }


    const departmentForm =
        document.getElementById(
            "departmentForm"
        );


    if (departmentForm) {

        departmentForm.addEventListener(
            "submit",
            saveDepartment
        );

    }

}


// =========================================================
// LOAD DEPARTMENTS
// =========================================================

async function loadDepartments(
    token,
    role
) {

    departmentTableBody.innerHTML = `
        <tr>
            <td colspan="5" class="empty-table">
                Loading departments...
            </td>
        </tr>
    `;


    try {

        const response =
            await fetch(
                "/departments/",
                {

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );


        if (response.status === 401) {

            logout();

            return;

        }


        if (response.status === 403) {

            departmentTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-table">
                        Access denied.
                    </td>
                </tr>
            `;

            return;

        }


        if (!response.ok) {

            departmentTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-table">
                        Unable to load departments.
                    </td>
                </tr>
            `;

            return;

        }


        const departments =
            await response.json();


        departmentTableBody.innerHTML = "";


        if (departments.length === 0) {

            departmentTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-table">
                        No departments found.
                    </td>
                </tr>
            `;

            return;

        }


        departments.forEach(
            function (department) {

                const row =
                    document.createElement(
                        "tr"
                    );


                let actions = "";


                if (role === "admin") {

                    actions = `

                        <button
                            class="edit-button"
                            onclick="editDepartment(
                                ${department.id},
                                '${escapeHtml(
                                    department.name
                                )}',
                                '${escapeHtml(
                                    department.description || ""
                                )}',
                                '${escapeHtml(
                                    department.is_active
                                )}'
                            )"
                        >
                            Edit
                        </button>


                        <button
                            class="delete-button"
                            onclick="deleteDepartment(
                                ${department.id}
                            )"
                        >
                            Delete
                        </button>

                    `;

                } else {

                    actions = `
                        <span class="view-only-text">
                            View only
                        </span>
                    `;

                }


                row.innerHTML = `

                    <td>
                        ${department.id}
                    </td>

                    <td>
                        <strong>
                            ${escapeHtml(
                                department.name
                            )}
                        </strong>
                    </td>

                    <td>
                        ${escapeHtml(
                            department.description || "-"
                        )}
                    </td>

                    <td>

                        <span
                            class="status-badge
                            ${
                                department.is_active ===
                                "Inactive"
                                ? "inactive-badge"
                                : ""
                            }"
                        >
                            ${escapeHtml(
                                department.is_active
                            )}
                        </span>

                    </td>

                    <td>
                        ${actions}
                    </td>

                `;


                departmentTableBody.appendChild(
                    row
                );

            }
        );


    } catch (error) {

        console.error(
            "Department loading error:",
            error
        );


        departmentTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-table">
                    Unable to connect to server.
                </td>
            </tr>
        `;

    }

}


// =========================================================
// OPEN CREATE FORM
// =========================================================

function openDepartmentCreateForm() {

    const formSection =
        document.getElementById(
            "departmentFormSection"
        );


    const title =
        document.getElementById(
            "departmentFormTitle"
        );


    const submitButton =
        document.getElementById(
            "departmentSubmitButton"
        );


    const editId =
        document.getElementById(
            "departmentEditId"
        );


    const name =
        document.getElementById(
            "departmentName"
        );


    const description =
        document.getElementById(
            "departmentDescription"
        );


    const status =
        document.getElementById(
            "departmentStatus"
        );


    editId.value = "";

    name.value = "";

    description.value = "";

    status.value = "Active";


    title.textContent =
        "Add New Department";


    submitButton.textContent =
        "Create Department";


    formSection.style.display =
        "block";


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


// =========================================================
// EDIT DEPARTMENT
// =========================================================

function editDepartment(
    departmentId,
    departmentName,
    description,
    status
) {

    const formSection =
        document.getElementById(
            "departmentFormSection"
        );


    const title =
        document.getElementById(
            "departmentFormTitle"
        );


    const submitButton =
        document.getElementById(
            "departmentSubmitButton"
        );


    document.getElementById(
        "departmentEditId"
    ).value =
        departmentId;


    document.getElementById(
        "departmentName"
    ).value =
        departmentName;


    document.getElementById(
        "departmentDescription"
    ).value =
        description;


    document.getElementById(
        "departmentStatus"
    ).value =
        status;


    title.textContent =
        "Edit Department";


    submitButton.textContent =
        "Update Department";


    formSection.style.display =
        "block";


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


// =========================================================
// SAVE DEPARTMENT
// =========================================================

async function saveDepartment(event) {

    event.preventDefault();


    const token =
        localStorage.getItem(
            "access_token"
        );


    const editId =
        document.getElementById(
            "departmentEditId"
        ).value;


    const name =
        document.getElementById(
            "departmentName"
        ).value.trim();


    const description =
        document.getElementById(
            "departmentDescription"
        ).value.trim();


    const status =
        document.getElementById(
            "departmentStatus"
        ).value;


    const message =
        document.getElementById(
            "departmentFormMessage"
        );


    if (!name) {

        message.textContent =
            "Department name is required.";

        return;

    }


    let url =
        "/departments/";


    let method =
        "POST";


    let body;


    if (editId) {

        url =
            "/departments/" +
            editId;


        method =
            "PUT";


        body = {

            name: name,

            description:
                description || null,

            is_active:
                status

        };

    } else {

        body = {

            name: name,

            description:
                description || null

        };

    }


    try {

        const response =
            await fetch(
                url,
                {

                    method: method,

                    headers: {

                        "Content-Type":
                            "application/json",

                        "Authorization":
                            "Bearer " + token

                    },

                    body:
                        JSON.stringify(body)

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            message.textContent =
                data.detail ||
                "Department operation failed.";

            return;

        }


        if (editId) {

            message.textContent =
                "Department updated successfully.";

        } else {

            message.textContent =
                "Department created successfully.";

        }


        document.getElementById(
            "departmentForm"
        ).reset();


        document.getElementById(
            "departmentEditId"
        ).value = "";


        loadDepartments(
            token,
            "admin"
        );


        setTimeout(function () {

            closeDepartmentForm();

            message.textContent = "";

        }, 1000);


    } catch (error) {

        console.error(error);

        message.textContent =
            "Unable to connect to server.";

    }

}


// =========================================================
// DELETE DEPARTMENT
// =========================================================

async function deleteDepartment(
    departmentId
) {

    const token =
        localStorage.getItem(
            "access_token"
        );


    const confirmed =
        confirm(
            "Are you sure you want to delete this department?"
        );


    if (!confirmed) {

        return;

    }


    try {

        const response =
            await fetch(
                "/departments/" +
                departmentId,
                {

                    method: "DELETE",

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Unable to delete department."
            );

            return;

        }


        alert(
            "Department deleted successfully."
        );


        loadDepartments(
            token,
            "admin"
        );


    } catch (error) {

        console.error(error);

        alert(
            "Unable to connect to server."
        );

    }

}


// =========================================================
// CLOSE DEPARTMENT FORM
// =========================================================

function closeDepartmentForm() {

    const formSection =
        document.getElementById(
            "departmentFormSection"
        );


    const form =
        document.getElementById(
            "departmentForm"
        );


    const message =
        document.getElementById(
            "departmentFormMessage"
        );


    form.reset();


    document.getElementById(
        "departmentEditId"
    ).value = "";


    formSection.style.display =
        "none";


    message.textContent = "";

}


// =========================================================
// HTML ESCAPING
// =========================================================

function escapeHtml(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


// =========================================================
// LOGOUT
// =========================================================

const logoutButton =
    document.getElementById(
        "logoutButton"
    );

if (logoutButton) {

    logoutButton.addEventListener(
        "click",
        logout
    );

}


function logout() {

    localStorage.removeItem(
        "access_token"
    );

    localStorage.removeItem(
        "username"
    );

    localStorage.removeItem(
        "role"
    );

    window.location.href = "/";

}