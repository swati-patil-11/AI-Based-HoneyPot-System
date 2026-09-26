// =========================================================
// PAYROLL MANAGEMENT UI
// =========================================================


// ---------------------------------------------------------
// Detect Payroll Page
// ---------------------------------------------------------

const employeePayrollSection =
    document.getElementById(
        "employeePayrollSection"
    );

const adminPayrollSection =
    document.getElementById(
        "adminPayrollSection"
    );


if (
    employeePayrollSection ||
    adminPayrollSection
) {

    initializePayrollPage();

}


// ---------------------------------------------------------
// Initialize Payroll Page
// ---------------------------------------------------------

function initializePayrollPage() {

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


    // -----------------------------------------------------
    // Authentication
    // -----------------------------------------------------

    if (!token) {

        window.location.href = "/";

        return;

    }


    // -----------------------------------------------------
    // Welcome
    // -----------------------------------------------------

    const welcome =
        document.getElementById(
            "payrollPageWelcome"
        );


    if (welcome) {

        welcome.textContent =
            "Welcome, " +
            username +
            " (" +
            role +
            ")";

    }


    // -----------------------------------------------------
    // Employee
    // -----------------------------------------------------

    if (role === "employee") {

        showEmployeePayroll();

        loadMySalary(token);

    }


    // -----------------------------------------------------
    // Admin / HR
    // -----------------------------------------------------

    else if (
        role === "admin" ||
        role === "hr"
    ) {

        showAdminPayroll();

        loadAllSalaries(token);

    }


    // -----------------------------------------------------
    // Other roles
    // -----------------------------------------------------

    else {

        showPayrollAccessDenied();

    }


    setupPayrollEventListeners();

}


// =========================================================
// SECTION VISIBILITY
// =========================================================

function showEmployeePayroll() {

    const employeeSection =
        document.getElementById(
            "employeePayrollSection"
        );

    const adminSection =
        document.getElementById(
            "adminPayrollSection"
        );

    const deniedSection =
        document.getElementById(
            "payrollAccessDenied"
        );


    if (employeeSection) {

        employeeSection.style.display =
            "block";

    }


    if (adminSection) {

        adminSection.style.display =
            "none";

    }


    if (deniedSection) {

        deniedSection.style.display =
            "none";

    }

}


function showAdminPayroll() {

    const employeeSection =
        document.getElementById(
            "employeePayrollSection"
        );

    const adminSection =
        document.getElementById(
            "adminPayrollSection"
        );

    const deniedSection =
        document.getElementById(
            "payrollAccessDenied"
        );


    if (employeeSection) {

        employeeSection.style.display =
            "none";

    }


    if (adminSection) {

        adminSection.style.display =
            "block";

    }


    if (deniedSection) {

        deniedSection.style.display =
            "none";

    }

}


function showPayrollAccessDenied() {

    const employeeSection =
        document.getElementById(
            "employeePayrollSection"
        );

    const adminSection =
        document.getElementById(
            "adminPayrollSection"
        );

    const deniedSection =
        document.getElementById(
            "payrollAccessDenied"
        );


    if (employeeSection) {

        employeeSection.style.display =
            "none";

    }


    if (adminSection) {

        adminSection.style.display =
            "none";

    }


    if (deniedSection) {

        deniedSection.style.display =
            "block";

    }

}


// =========================================================
// EVENT LISTENERS
// =========================================================

function setupPayrollEventListeners() {

    const salaryForm =
        document.getElementById(
            "salaryForm"
        );


    if (salaryForm) {

        salaryForm.addEventListener(
            "submit",
            createSalary
        );

    }


    const refreshButton =
        document.getElementById(
            "refreshSalaryButton"
        );


    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            function () {

                const token =
                    localStorage.getItem(
                        "access_token"
                    );

                loadAllSalaries(token);

            }
        );

    }

}


// =========================================================
// EMPLOYEE SALARY
// =========================================================

async function loadMySalary(token) {

    const message =
        document.getElementById(
            "employeeSalaryMessage"
        );


    try {

        const response =
            await fetch(
                "/salary/me",
                {

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );


        if (response.status === 401) {

            logoutFromPayroll();

            return;

        }


        const data =
            await response.json();


        if (!response.ok) {

            message.textContent =
                data.detail ||
                "Unable to load salary.";

            return;

        }


        const currency =
            data.currency || "INR";


        document.getElementById(
            "mySalaryEmployee"
        ).textContent =
            data.employee_name;


        document.getElementById(
            "myBasicSalary"
        ).textContent =
            formatCurrency(
                data.basic_salary,
                currency
            );


        document.getElementById(
            "myAllowances"
        ).textContent =
            formatCurrency(
                data.allowances,
                currency
            );


        document.getElementById(
            "myDeductions"
        ).textContent =
            formatCurrency(
                data.deductions,
                currency
            );


        document.getElementById(
            "myNetSalary"
        ).textContent =
            formatCurrency(
                data.net_salary,
                currency
            );


        document.getElementById(
            "breakdownBasic"
        ).textContent =
            formatCurrency(
                data.basic_salary,
                currency
            );


        document.getElementById(
            "breakdownAllowances"
        ).textContent =
            formatCurrency(
                data.allowances,
                currency
            );


        document.getElementById(
            "breakdownDeductions"
        ).textContent =
            formatCurrency(
                data.deductions,
                currency
            );


        document.getElementById(
            "breakdownNet"
        ).textContent =
            formatCurrency(
                data.net_salary,
                currency
            );


        message.textContent = "";


    } catch (error) {

        console.error(
            "Salary loading error:",
            error
        );


        message.textContent =
            "Unable to connect to server.";

    }

}


// =========================================================
// ADMIN / HR SALARY LIST
// =========================================================

async function loadAllSalaries(token) {

    const tableBody =
        document.getElementById(
            "salaryTableBody"
        );


    if (!tableBody) {

        return;

    }


    tableBody.innerHTML = `
        <tr>
            <td colspan="9" class="empty-table">
                Loading salary records...
            </td>
        </tr>
    `;


    try {

        const response =
            await fetch(
                "/salary/",
                {

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );


        if (response.status === 401) {

            logoutFromPayroll();

            return;

        }


        if (response.status === 403) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-table">
                        Access denied.
                    </td>
                </tr>
            `;

            return;

        }


        const records =
            await response.json();


        if (!response.ok) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-table">
                        ${
                            records.detail ||
                            "Unable to load salaries."
                        }
                    </td>
                </tr>
            `;

            return;

        }


        tableBody.innerHTML = "";


        if (records.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-table">
                        No salary records found.
                    </td>
                </tr>
            `;

            return;

        }


        records.forEach(
            function (record) {

                const row =
                    document.createElement(
                        "tr"
                    );


                row.innerHTML = `

                    <td>
                        ${record.salary_id}
                    </td>

                    <td>
                        ${record.employee_id}
                    </td>

                    <td>
                        ${escapePayrollHtml(
                            record.employee_code
                        )}
                    </td>

                    <td>
                        ${escapePayrollHtml(
                            record.employee_name
                        )}
                    </td>

                    <td>
                        ${formatCurrency(
                            record.basic_salary,
                            record.currency
                        )}
                    </td>

                    <td>
                        ${formatCurrency(
                            record.allowances,
                            record.currency
                        )}
                    </td>

                    <td>
                        ${formatCurrency(
                            record.deductions,
                            record.currency
                        )}
                    </td>

                    <td>
                        <strong>
                            ${formatCurrency(
                                record.net_salary,
                                record.currency
                            )}
                        </strong>
                    </td>

                    <td>
                        ${escapePayrollHtml(
                            record.currency
                        )}
                    </td>

                `;


                tableBody.appendChild(
                    row
                );

            }
        );


    } catch (error) {

        console.error(
            "Salary loading error:",
            error
        );


        tableBody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-table">
                    Unable to connect to server.
                </td>
            </tr>
        `;

    }

}


// =========================================================
// CREATE SALARY
// =========================================================

async function createSalary(event) {

    event.preventDefault();


    const token =
        localStorage.getItem(
            "access_token"
        );


    const message =
        document.getElementById(
            "salaryFormMessage"
        );


    const button =
        document.getElementById(
            "createSalaryButton"
        );


    const employeeId =
        Number(
            document.getElementById(
                "salaryEmployeeId"
            ).value
        );


    const basicSalary =
        Number(
            document.getElementById(
                "basicSalaryInput"
            ).value
        );


    const allowances =
        Number(
            document.getElementById(
                "allowancesInput"
            ).value || 0
        );


    const deductions =
        Number(
            document.getElementById(
                "deductionsInput"
            ).value || 0
        );


    const currency =
        document.getElementById(
            "currencyInput"
        ).value;


    if (
        !employeeId ||
        employeeId < 1
    ) {

        message.textContent =
            "Enter a valid employee database ID.";

        return;

    }


    if (basicSalary < 0) {

        message.textContent =
            "Basic salary cannot be negative.";

        return;

    }


    if (allowances < 0) {

        message.textContent =
            "Allowances cannot be negative.";

        return;

    }


    if (deductions < 0) {

        message.textContent =
            "Deductions cannot be negative.";

        return;

    }


    button.disabled = true;


    message.textContent =
        "Creating salary record...";


    try {

        const response =
            await fetch(
                "/salary/",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json",

                        "Authorization":
                            "Bearer " + token

                    },

                    body:
                        JSON.stringify({

                            employee_id:
                                employeeId,

                            basic_salary:
                                basicSalary,

                            allowances:
                                allowances,

                            deductions:
                                deductions,

                            currency:
                                currency

                        })

                }
            );


        const data =
            await response.json();


        if (response.status === 401) {

            logoutFromPayroll();

            return;

        }


        if (!response.ok) {

            message.textContent =
                data.detail ||
                "Unable to create salary record.";

            return;

        }


        message.textContent =
            "Salary record created successfully.";


        document.getElementById(
            "salaryForm"
        ).reset();


        document.getElementById(
            "allowancesInput"
        ).value = "0";


        document.getElementById(
            "deductionsInput"
        ).value = "0";


        document.getElementById(
            "currencyInput"
        ).value = "INR";


        loadAllSalaries(token);


    } catch (error) {

        console.error(
            "Salary creation error:",
            error
        );


        message.textContent =
            "Unable to connect to server.";

    } finally {

        button.disabled = false;

    }

}


// =========================================================
// FORMAT CURRENCY
// =========================================================

function formatCurrency(
    amount,
    currency
) {

    const value =
        Number(amount || 0);


    if (currency === "INR") {

        return (
            "₹" +
            value.toLocaleString(
                "en-IN",
                {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }
            )
        );

    }


    return (
        currency +
        " " +
        value.toLocaleString(
            "en-US",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        )
    );

}


// =========================================================
// HTML ESCAPING
// =========================================================

function escapePayrollHtml(value) {

    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


// =========================================================
// LOGOUT
// =========================================================

function logoutFromPayroll() {

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