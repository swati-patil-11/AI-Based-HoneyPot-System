// =========================================================
// PAYROLL MANAGEMENT
// =========================================================


document.addEventListener(
    "DOMContentLoaded",
    () => {

        const employeeSection =
            document.getElementById(
                "employeePayrollSection"
            );

        const adminSection =
            document.getElementById(
                "adminPayrollSection"
            );

        if (
            employeeSection ||
            adminSection
        ) {
            initializePayrollPage();
        }

    }
);


// =========================================================
// INITIALIZE
// =========================================================

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


    if (!token) {

        window.location.href = "/";

        return;
    }


    const welcome =
        document.getElementById(
            "payrollPageWelcome"
        );


    if (welcome) {

        welcome.textContent =
            `Welcome, ${username} (${role})`;
    }


    if (role === "employee") {

        showEmployeePayroll();

        loadMySalary(token);

    }

    else if (
        role === "admin" ||
        role === "hr"
    ) {

        showAdminPayroll();

        loadAllSalaries(token);

    }

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
            () => {

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
// LOAD MY SALARY
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

            if (message) {

                message.textContent =
                    data.detail ||
                    "Unable to load salary.";

                message.className =
                    "message error-message";
            }

            return;
        }


        const currency =
            data.currency || "INR";


        document.getElementById(
            "mySalaryEmployee"
        ).textContent =
            `${data.employee_id} - ${data.employee_name}`;


        document.getElementById(
            "myBasicSalary"
        ).textContent =
            formatPayrollCurrency(
                data.basic_salary,
                currency
            );


        document.getElementById(
            "myAllowances"
        ).textContent =
            formatPayrollCurrency(
                data.allowances,
                currency
            );


        document.getElementById(
            "myDeductions"
        ).textContent =
            formatPayrollCurrency(
                data.deductions,
                currency
            );


        document.getElementById(
            "myNetSalary"
        ).textContent =
            formatPayrollCurrency(
                data.net_salary,
                currency
            );


        document.getElementById(
            "breakdownBasic"
        ).textContent =
            formatPayrollCurrency(
                data.basic_salary,
                currency
            );


        document.getElementById(
            "breakdownAllowances"
        ).textContent =
            formatPayrollCurrency(
                data.allowances,
                currency
            );


        document.getElementById(
            "breakdownDeductions"
        ).textContent =
            formatPayrollCurrency(
                data.deductions,
                currency
            );


        document.getElementById(
            "breakdownNet"
        ).textContent =
            formatPayrollCurrency(
                data.net_salary,
                currency
            );


        if (message) {

            message.textContent = "";
            message.className = "message";
        }


    } catch (error) {

        console.error(
            "Salary loading error:",
            error
        );

        if (message) {

            message.textContent =
                "Unable to connect to server.";

            message.className =
                "message error-message";
        }
    }
}


// =========================================================
// LOAD ALL SALARIES
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
            <td colspan="8" class="empty-table">
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


        const records =
            await response.json();


        if (!response.ok) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-table">
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


        if (!records.length) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-table">
                        No salary records found.
                    </td>
                </tr>
            `;

            return;
        }


        records.forEach(record => {

            const row =
                document.createElement("tr");


            row.innerHTML = `

                <td>
                    ${escapePayrollHtml(
                        record.salary_id
                    )}
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
                    ${formatPayrollCurrency(
                        record.basic_salary,
                        record.currency
                    )}
                </td>

                <td>
                    ${formatPayrollCurrency(
                        record.allowances,
                        record.currency
                    )}
                </td>

                <td>
                    ${formatPayrollCurrency(
                        record.deductions,
                        record.currency
                    )}
                </td>

                <td>
                    <strong>
                        ${formatPayrollCurrency(
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


            tableBody.appendChild(row);
        });


    } catch (error) {

        console.error(
            "Salary loading error:",
            error
        );


        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-table">
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


    const employeeCode =
        document.getElementById(
            "salaryEmployeeId"
        ).value
            .trim()
            .toUpperCase();


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


    if (!employeeCode) {

        showPayrollMessage(
            "Enter Employee Code, for example EMP001.",
            "error"
        );

        return;
    }


    if (
        !Number.isFinite(basicSalary) ||
        basicSalary < 0
    ) {

        showPayrollMessage(
            "Enter a valid basic salary.",
            "error"
        );

        return;
    }


    if (
        !Number.isFinite(allowances) ||
        allowances < 0
    ) {

        showPayrollMessage(
            "Allowances cannot be negative.",
            "error"
        );

        return;
    }


    if (
        !Number.isFinite(deductions) ||
        deductions < 0
    ) {

        showPayrollMessage(
            "Deductions cannot be negative.",
            "error"
        );

        return;
    }


    button.disabled = true;


    showPayrollMessage(
        "Creating salary record...",
        ""
    );


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
                                employeeCode,

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

            showPayrollMessage(
                data.detail ||
                "Unable to create salary record.",
                "error"
            );

            return;
        }


        showPayrollMessage(
            `Salary saved for ${
                data.salary.employee_code
            } - ${
                data.salary.employee_name
            }.`,
            "success"
        );


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


        await loadAllSalaries(token);


    } catch (error) {

        console.error(
            "Salary creation error:",
            error
        );


        showPayrollMessage(
            "Unable to connect to server.",
            "error"
        );


    } finally {

        button.disabled = false;
    }
}


// =========================================================
// MESSAGE
// =========================================================

function showPayrollMessage(
    text,
    type
) {

    const message =
        document.getElementById(
            "salaryFormMessage"
        );


    if (!message) {
        return;
    }


    message.textContent = text;


    if (type === "success") {

        message.className =
            "message success-message";
    }

    else if (type === "error") {

        message.className =
            "message error-message";
    }

    else {

        message.className =
            "message";
    }
}


// =========================================================
// CURRENCY
// =========================================================

function formatPayrollCurrency(
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
// HTML ESCAPE
// =========================================================

function escapePayrollHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }


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