// =========================================================
// ATTENDANCE MANAGEMENT UI
// =========================================================


// ---------------------------------------------------------
// Check whether this is the Attendance page
// ---------------------------------------------------------

const employeeAttendanceSection =
    document.getElementById(
        "employeeAttendanceSection"
    );


const adminAttendanceSection =
    document.getElementById(
        "adminAttendanceSection"
    );


if (
    employeeAttendanceSection ||
    adminAttendanceSection
) {

    initializeAttendancePage();

}


// ---------------------------------------------------------
// Initialize Attendance Page
// ---------------------------------------------------------

function initializeAttendancePage() {

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
    // Authentication check
    // -----------------------------------------------------

    if (!token) {

        window.location.href = "/";

        return;

    }


    // -----------------------------------------------------
    // Welcome message
    // -----------------------------------------------------

    const welcome =
        document.getElementById(
            "attendancePageWelcome"
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
    // Today's date
    // -----------------------------------------------------

    const today =
        getLocalDate();


    const todayDateElement =
        document.getElementById(
            "todayAttendanceDate"
        );


    if (todayDateElement) {

        todayDateElement.textContent =
            formatDisplayDate(today);

    }


    // -----------------------------------------------------
    // Employee
    // -----------------------------------------------------

    if (role === "employee") {

        showEmployeeAttendance();

        loadMyAttendance(token);

    }


    // -----------------------------------------------------
    // Admin / HR
    // -----------------------------------------------------

    else if (
        role === "admin" ||
        role === "hr"
    ) {

        showAdminAttendance();

        loadAllAttendance(
            token,
            role
        );

    }


    // -----------------------------------------------------
    // Unknown role
    // -----------------------------------------------------

    else {

        showAttendanceAccessDenied();

    }


    // -----------------------------------------------------
    // Event listeners
    // -----------------------------------------------------

    setupAttendanceEventListeners();

}


// ---------------------------------------------------------
// Show Employee Attendance
// ---------------------------------------------------------

function showEmployeeAttendance() {

    const employeeSection =
        document.getElementById(
            "employeeAttendanceSection"
        );


    const adminSection =
        document.getElementById(
            "adminAttendanceSection"
        );


    const deniedSection =
        document.getElementById(
            "attendanceAccessDenied"
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


// ---------------------------------------------------------
// Show Admin / HR Attendance
// ---------------------------------------------------------

function showAdminAttendance() {

    const employeeSection =
        document.getElementById(
            "employeeAttendanceSection"
        );


    const adminSection =
        document.getElementById(
            "adminAttendanceSection"
        );


    const deniedSection =
        document.getElementById(
            "attendanceAccessDenied"
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


// ---------------------------------------------------------
// Show Access Denied
// ---------------------------------------------------------

function showAttendanceAccessDenied() {

    const employeeSection =
        document.getElementById(
            "employeeAttendanceSection"
        );


    const adminSection =
        document.getElementById(
            "adminAttendanceSection"
        );


    const deniedSection =
        document.getElementById(
            "attendanceAccessDenied"
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


// ---------------------------------------------------------
// Event Listeners
// ---------------------------------------------------------

function setupAttendanceEventListeners() {

    // Employee attendance form

    const attendanceForm =
        document.getElementById(
            "attendanceForm"
        );


    if (attendanceForm) {

        attendanceForm.addEventListener(
            "submit",
            markAttendance
        );

    }


    // Refresh employee attendance

    const refreshMyButton =
        document.getElementById(
            "refreshMyAttendanceButton"
        );


    if (refreshMyButton) {

        refreshMyButton.addEventListener(
            "click",
            function () {

                const token =
                    localStorage.getItem(
                        "access_token"
                    );


                loadMyAttendance(token);

            }
        );

    }


    // Apply admin filter

    const applyFilterButton =
        document.getElementById(
            "applyAttendanceFilterButton"
        );


    if (applyFilterButton) {

        applyFilterButton.addEventListener(
            "click",
            function () {

                const token =
                    localStorage.getItem(
                        "access_token"
                    );


                const role =
                    localStorage.getItem(
                        "role"
                    );


                loadAllAttendance(
                    token,
                    role
                );

            }
        );

    }


    // Clear filters

    const clearFilterButton =
        document.getElementById(
            "clearAttendanceFilterButton"
        );


    if (clearFilterButton) {

        clearFilterButton.addEventListener(
            "click",
            function () {

                document.getElementById(
                    "attendanceFilterDate"
                ).value = "";


                document.getElementById(
                    "attendanceFilterEmployee"
                ).value = "";


                const token =
                    localStorage.getItem(
                        "access_token"
                    );


                const role =
                    localStorage.getItem(
                        "role"
                    );


                loadAllAttendance(
                    token,
                    role
                );

            }
        );

    }


    // Refresh admin table

    const refreshAllButton =
        document.getElementById(
            "refreshAllAttendanceButton"
        );


    if (refreshAllButton) {

        refreshAllButton.addEventListener(
            "click",
            function () {

                const token =
                    localStorage.getItem(
                        "access_token"
                    );


                const role =
                    localStorage.getItem(
                        "role"
                    );


                loadAllAttendance(
                    token,
                    role
                );

            }
        );

    }

}


// =========================================================
// EMPLOYEE FUNCTIONS
// =========================================================


// ---------------------------------------------------------
// Mark Attendance
// ---------------------------------------------------------

async function markAttendance(event) {

    event.preventDefault();


    const token =
        localStorage.getItem(
            "access_token"
        );


    const status =
        document.getElementById(
            "attendanceStatus"
        ).value;


    const remarks =
        document.getElementById(
            "attendanceRemarks"
        ).value.trim();


    const message =
        document.getElementById(
            "attendanceFormMessage"
        );


    const button =
        document.getElementById(
            "markAttendanceButton"
        );


    button.disabled = true;


    message.textContent =
        "Saving attendance...";


    try {

        const response =
            await fetch(
                "/attendance/me",
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

                            status:
                                status,

                            remarks:
                                remarks || null

                        })

                }
            );


        const data =
            await response.json();


        if (response.status === 401) {

            logoutFromAttendance();

            return;

        }


        if (!response.ok) {

            message.textContent =
                data.detail ||
                "Unable to mark attendance.";

            return;

        }


        message.textContent =
            "Attendance marked successfully.";


        document.getElementById(
            "attendanceRemarks"
        ).value = "";


        showTodayAttendance(
            data.attendance
        );


        loadMyAttendance(token);


    } catch (error) {

        console.error(
            "Attendance error:",
            error
        );


        message.textContent =
            "Unable to connect to server.";

    } finally {

        button.disabled = false;

    }

}


// ---------------------------------------------------------
// Load My Attendance
// ---------------------------------------------------------

async function loadMyAttendance(token) {

    const tableBody =
        document.getElementById(
            "myAttendanceTableBody"
        );


    if (!tableBody) {

        return;

    }


    tableBody.innerHTML = `
        <tr>
            <td colspan="3" class="empty-table">
                Loading attendance...
            </td>
        </tr>
    `;


    try {

        const response =
            await fetch(
                "/attendance/me",
                {

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );


        if (response.status === 401) {

            logoutFromAttendance();

            return;

        }


        if (!response.ok) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-table">
                        Unable to load attendance.
                    </td>
                </tr>
            `;

            return;

        }


        const data =
            await response.json();


        const records =
            data.attendance || [];


        updateTodayAttendanceFromHistory(
            records
        );


        tableBody.innerHTML = "";


        if (records.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-table">
                        No attendance records found.
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
                        ${formatDisplayDate(
                            record.attendance_date
                        )}
                    </td>

                    <td>

                        <span
                            class="status-badge
                            ${getAttendanceStatusClass(
                                record.status
                            )}"
                        >
                            ${escapeAttendanceHtml(
                                record.status
                            )}
                        </span>

                    </td>

                    <td>
                        ${escapeAttendanceHtml(
                            record.remarks || "-"
                        )}
                    </td>

                `;


                tableBody.appendChild(row);

            }
        );


    } catch (error) {

        console.error(
            "My attendance loading error:",
            error
        );


        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="empty-table">
                    Unable to connect to server.
                </td>
            </tr>
        `;

    }

}


// ---------------------------------------------------------
// Show Today's Attendance
// ---------------------------------------------------------

function showTodayAttendance(attendance) {

    const result =
        document.getElementById(
            "todayAttendanceResult"
        );


    if (!result) {

        return;

    }


    result.innerHTML = `

        <div class="today-attendance-card">

            <div>

                <strong>
                    ${escapeAttendanceHtml(
                        attendance.status
                    )}
                </strong>

                <span
                    class="status-badge
                    ${getAttendanceStatusClass(
                        attendance.status
                    )}"
                >
                    ${escapeAttendanceHtml(
                        attendance.status
                    )}
                </span>

            </div>

            <p>

                Remarks:
                ${escapeAttendanceHtml(
                    attendance.remarks || "None"
                )}

            </p>

        </div>

    `;

}


// ---------------------------------------------------------
// Update Today's Attendance from history
// ---------------------------------------------------------

function updateTodayAttendanceFromHistory(
    records
) {

    const today =
        getLocalDate();


    const todayRecord =
        records.find(
            function (record) {

                return record.attendance_date ===
                    today;

            }
        );


    if (todayRecord) {

        showTodayAttendance(
            todayRecord
        );

    } else {

        const result =
            document.getElementById(
                "todayAttendanceResult"
            );


        if (result) {

            result.innerHTML = `
                <p>
                    No attendance has been
                    recorded for today.
                </p>
            `;

        }

    }

}


// =========================================================
// ADMIN / HR FUNCTIONS
// =========================================================


// ---------------------------------------------------------
// Load All Attendance
// ---------------------------------------------------------

async function loadAllAttendance(
    token,
    role
) {

    const tableBody =
        document.getElementById(
            "allAttendanceTableBody"
        );


    if (!tableBody) {

        return;

    }


    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="empty-table">
                Loading attendance...
            </td>
        </tr>
    `;


    const date =
        document.getElementById(
            "attendanceFilterDate"
        ).value;


    const employeeId =
        document.getElementById(
            "attendanceFilterEmployee"
        ).value;


    const params =
        new URLSearchParams();


    if (date) {

        params.append(
            "attendance_date",
            date
        );

    }


    if (employeeId) {

        params.append(
            "employee_id",
            employeeId
        );

    }


    let url =
        "/attendance/";


    if (params.toString()) {

        url +=
            "?" +
            params.toString();

    }


    try {

        const response =
            await fetch(
                url,
                {

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );


        if (response.status === 401) {

            logoutFromAttendance();

            return;

        }


        if (response.status === 403) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-table">
                        Access denied.
                    </td>
                </tr>
            `;

            return;

        }


        if (!response.ok) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-table">
                        Unable to load attendance.
                    </td>
                </tr>
            `;

            return;

        }


        const records =
            await response.json();


        tableBody.innerHTML = "";


        if (records.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-table">
                        No attendance records found.
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
                        ${record.attendance_id}
                    </td>

                    <td>
                        ${record.employee_id}
                    </td>

                    <td>
                        ${escapeAttendanceHtml(
                            record.employee_code
                        )}
                    </td>

                    <td>
                        ${escapeAttendanceHtml(
                            record.employee_name
                        )}
                    </td>

                    <td>
                        ${formatDisplayDate(
                            record.attendance_date
                        )}
                    </td>

                    <td>

                        <span
                            class="status-badge
                            ${getAttendanceStatusClass(
                                record.status
                            )}"
                        >
                            ${escapeAttendanceHtml(
                                record.status
                            )}
                        </span>

                    </td>

                    <td>
                        ${escapeAttendanceHtml(
                            record.remarks || "-"
                        )}
                    </td>

                `;


                tableBody.appendChild(row);

            }
        );


    } catch (error) {

        console.error(
            "All attendance loading error:",
            error
        );


        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-table">
                    Unable to connect to server.
                </td>
            </tr>
        `;

    }

}


// =========================================================
// UTILITY FUNCTIONS
// =========================================================


// ---------------------------------------------------------
// Get Local Date
// ---------------------------------------------------------

function getLocalDate() {

    const now =
        new Date();


    const year =
        now.getFullYear();


    const month =
        String(
            now.getMonth() + 1
        ).padStart(
            2,
            "0"
        );


    const day =
        String(
            now.getDate()
        ).padStart(
            2,
            "0"
        );


    return (
        year +
        "-" +
        month +
        "-" +
        day
    );

}


// ---------------------------------------------------------
// Display Date
// ---------------------------------------------------------

function formatDisplayDate(
    dateString
) {

    if (!dateString) {

        return "-";

    }


    const parts =
        dateString.split("-");


    if (parts.length !== 3) {

        return dateString;

    }


    return (
        parts[2] +
        "-" +
        parts[1] +
        "-" +
        parts[0]
    );

}


// ---------------------------------------------------------
// Attendance Status CSS
// ---------------------------------------------------------

function getAttendanceStatusClass(
    status
) {

    if (status === "Absent") {

        return "attendance-absent";

    }


    if (status === "Leave") {

        return "attendance-leave";

    }


    return "attendance-present";

}


// ---------------------------------------------------------
// HTML escaping
// ---------------------------------------------------------

function escapeAttendanceHtml(
    value
) {

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


// ---------------------------------------------------------
// Logout
// ---------------------------------------------------------

function logoutFromAttendance() {

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