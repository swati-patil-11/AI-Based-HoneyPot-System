// ============================================================
// EMPLOYEE MANAGEMENT
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    const addButton = document.getElementById("showAddEmployeeButton");
    const formSection = document.getElementById("addEmployeeSection");
    const employeeForm = document.getElementById("employeeForm");
    const cancelButton = document.getElementById("cancelEmployeeButton");
    const refreshButton = document.getElementById("refreshEmployeesButton");
    const tableBody = document.getElementById("employeeTableBody");
    const message = document.getElementById("employeeFormMessage");

    // ========================================================
    // VALIDATION PATTERNS
    // ========================================================

    const namePattern = /^[A-Za-z]+$/;
    const phonePattern = /^\d{10}$/;

    // ========================================================
// REAL-TIME INPUT VALIDATION
// ========================================================

// First Name - letters only
const firstNameInput = document.getElementById("firstName");

if (firstNameInput) {
    firstNameInput.addEventListener("input", () => {
        firstNameInput.value =
            firstNameInput.value.replace(/[^A-Za-z]/g, "");
    });
}


// Last Name - letters only
const lastNameInput = document.getElementById("lastName");

if (lastNameInput) {
    lastNameInput.addEventListener("input", () => {
        lastNameInput.value =
            lastNameInput.value.replace(/[^A-Za-z]/g, "");
    });
}


// Phone - digits only, maximum 10 digits
const phoneInput = document.getElementById("phone");

if (phoneInput) {
    phoneInput.addEventListener("input", () => {

        phoneInput.value =
            phoneInput.value
                .replace(/\D/g, "")
                .slice(0, 10);
    });
}


// Designation - letters only
const designationInput =
    document.getElementById("designation");

if (designationInput) {
    designationInput.addEventListener("input", () => {
        designationInput.value =
            designationInput.value.replace(/[^A-Za-z]/g, "");
    });
}

// Department ID - positive digits only
const departmentIdInput =
    document.getElementById("departmentId");

if (departmentIdInput) {
    departmentIdInput.addEventListener("input", () => {

        departmentIdInput.value =
            departmentIdInput.value
                .replace(/\D/g, "");
    });
}
    // ========================================================
    // SHOW ADD EMPLOYEE FORM
    // ========================================================

    if (addButton && formSection) {

        addButton.addEventListener("click", () => {

            formSection.style.display = "block";

            formSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            const firstField =
                document.getElementById("employeeId");

            if (firstField) {
                setTimeout(() => {
                    firstField.focus();
                }, 300);
            }
        });
    }

    // ========================================================
    // CANCEL ADD EMPLOYEE
    // ========================================================

    if (cancelButton && formSection) {

        cancelButton.addEventListener("click", () => {

            if (employeeForm) {
                employeeForm.reset();
            }

            formSection.style.display = "none";

            if (message) {
                message.textContent = "";
                message.className = "message";
            }
        });
    }

    // ========================================================
    // SHOW MESSAGE
    // ========================================================

    function showMessage(text, type = "error") {

        if (!message) {
            alert(text);
            return;
        }

        message.textContent = text;

        if (type === "success") {
            message.className =
                "message success-message";
        } else {
            message.className =
                "message error-message";
        }
    }

    // ========================================================
    // VALIDATE EMPLOYEE DATA
    // ========================================================

    function validateEmployeeData(employeeData) {

        // ----------------------------------------------------
        // Employee ID
        // ----------------------------------------------------

        if (!employeeData.employee_id) {
            return "Employee ID is required.";
        }

        // ----------------------------------------------------
        // First Name
        // ----------------------------------------------------

        if (!employeeData.first_name) {
            return "First Name is required.";
        }

        if (!namePattern.test(employeeData.first_name)) {
            return "First Name must contain characters only.";
        }

        // ----------------------------------------------------
        // Last Name
        // ----------------------------------------------------

        if (!employeeData.last_name) {
            return "Last Name is required.";
        }

        if (!namePattern.test(employeeData.last_name)) {
            return "Last Name must contain characters only.";
        }

        // ----------------------------------------------------
        // Email
        // ----------------------------------------------------

        if (!employeeData.email) {
            return "Email is required.";
        }

        // ----------------------------------------------------
        // Phone
        // ----------------------------------------------------

        if (
            employeeData.phone &&
            !phonePattern.test(employeeData.phone)
        ) {
            return "Phone number must contain exactly 10 digits.";
        }

        // ----------------------------------------------------
        // Department
        // ----------------------------------------------------

        if (
            !employeeData.department_id ||
            Number.isNaN(employeeData.department_id)
        ) {
            return "Department is required.";
        }

        // ----------------------------------------------------
        // Designation
        // ----------------------------------------------------

        if (!employeeData.designation) {
            return "Designation is required.";
        }

        if (!namePattern.test(employeeData.designation)) {
            return "Designation must contain characters only.";
        }

        // ----------------------------------------------------
        // Joining Date
        // ----------------------------------------------------

        if (!employeeData.joining_date) {
            return "Joining date is required.";
        }

        return null;
    }

    // ========================================================
    // LOAD EMPLOYEES
    // ========================================================

    async function loadEmployees() {

        if (!tableBody) {
            return;
        }

        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-table">
                    Loading employees...
                </td>
            </tr>
        `;

        try {

            const response =
                await apiFetch("/employees/");

            if (response.status === 401) {
                logout();
                return;
            }

            if (!response.ok) {

                const data =
                    await response.json().catch(() => ({}));

                throw new Error(
                    data.detail ||
                    "Unable to load employees."
                );
            }

            const data =
                await response.json();

            const employees =
                Array.isArray(data)
                    ? data
                    : (data.employees || []);

            renderEmployees(employees);

        } catch (error) {

            console.error(error);

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-table">
                        ${escapeHtml(error.message)}
                    </td>
                </tr>
            `;
        }
    }

    // ========================================================
    // RENDER EMPLOYEES
    // ========================================================

    function renderEmployees(employees) {

        if (!employees.length) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-table">
                        No employees found.
                    </td>
                </tr>
            `;

            return;
        }

        tableBody.innerHTML = "";

        employees.forEach(employee => {

            const row =
                document.createElement("tr");

            const fullName =
                `${employee.first_name || ""} ${employee.last_name || ""}`
                    .trim();

            let actionHtml = "";

            // =================================================
            // ADMIN
            // =================================================

            if (getRole() === "admin") {

                actionHtml = `
                    <button
                        type="button"
                        class="edit-button small-button"
                        data-edit-id="${employee.id}"
                    >
                        Edit
                    </button>

                    <button
                        type="button"
                        class="delete-button small-button"
                        data-delete-id="${employee.id}"
                    >
                        Delete
                    </button>
                `;
            }

            // =================================================
            // HR
            // =================================================

            else if (getRole() === "hr") {

                actionHtml = `
                    <button
                        type="button"
                        class="edit-button small-button"
                        data-edit-id="${employee.id}"
                    >
                        Edit
                    </button>
                `;
            }

            // =================================================
            // EMPLOYEE
            // =================================================

            else {

                actionHtml = `
                    <span class="view-only-action">
                        View Only
                    </span>
                `;
            }

            row.innerHTML = `
                <td>
                    ${escapeHtml(employee.id)}
                </td>

                <td>
                    ${escapeHtml(
                        employee.employee_id || "-"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        fullName || "-"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        employee.email || "-"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        employee.department_id ?? "-"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        employee.designation || "-"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        employee.employment_status || "-"
                    )}
                </td>

                <td>
                    ${actionHtml}
                </td>
            `;

            tableBody.appendChild(row);
        });

        // ====================================================
        // EDIT EVENTS
        // ====================================================

        tableBody
            .querySelectorAll("[data-edit-id]")
            .forEach(button => {

                button.addEventListener(
                    "click",
                    async () => {

                        const employeeId =
                            button.dataset.editId;

                        await editEmployee(employeeId);
                    }
                );
            });

        // ====================================================
        // DELETE EVENTS
        // ====================================================

        tableBody
            .querySelectorAll("[data-delete-id]")
            .forEach(button => {

                button.addEventListener(
                    "click",
                    async () => {

                        const employeeId =
                            button.dataset.deleteId;

                        await deleteEmployee(employeeId);
                    }
                );
            });
    }

    // ========================================================
    // CREATE EMPLOYEE
    // ========================================================

    if (employeeForm) {

        employeeForm.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();

                const employeeData = {

                    employee_id:
                        document
                            .getElementById("employeeId")
                            .value
                            .trim(),

                    first_name:
                        document
                            .getElementById("firstName")
                            .value
                            .trim(),

                    last_name:
                        document
                            .getElementById("lastName")
                            .value
                            .trim(),

                    email:
                        document
                            .getElementById("email")
                            .value
                            .trim(),

                    phone:
                        document
                            .getElementById("phone")
                            .value
                            .trim() || null,

                    department_id:
                        Number(
                            document
                                .getElementById("departmentId")
                                .value
                        ),

                    designation:
                        document
                            .getElementById("designation")
                            .value
                            .trim(),

                    joining_date:
                        document
                            .getElementById("joiningDate")
                            .value,

                    employment_status:
                        document
                            .getElementById("employmentStatus")
                            .value
                };

                // ------------------------------------------------
                // FRONTEND VALIDATION
                // ------------------------------------------------

                const validationError =
                    validateEmployeeData(employeeData);

                if (validationError) {

                    showMessage(
                        validationError,
                        "error"
                    );

                    return;
                }

                showMessage(
                    "Creating employee...",
                    "normal"
                );

                try {

                    const response =
                        await apiFetch(
                            "/employees/",
                            {
                                method: "POST",
                                body: JSON.stringify(
                                    employeeData
                                )
                            }
                        );

                    const data =
                        await response
                            .json()
                            .catch(() => ({}));

                    if (!response.ok) {

                        throw new Error(
                            data.detail ||
                            "Unable to create employee."
                        );
                    }

                    showMessage(
                        "Employee created successfully.",
                        "success"
                    );

                    employeeForm.reset();

                    await loadEmployees();

                    setTimeout(() => {

                        formSection.style.display =
                            "none";

                        if (message) {
                            message.textContent = "";
                            message.className =
                                "message";
                        }

                    }, 1200);

                } catch (error) {

                    console.error(error);

                    showMessage(
                        error.message ||
                        "Unable to create employee.",
                        "error"
                    );
                }
            }
        );
    }

    // ========================================================
    // EDIT EMPLOYEE
    // ========================================================

    async function editEmployee(employeeId) {

        try {

            const response =
                await apiFetch(
                    `/employees/${employeeId}`
                );

            const employee =
                await response
                    .json()
                    .catch(() => ({}));

            if (!response.ok) {

                throw new Error(
                    employee.detail ||
                    "Unable to load employee."
                );
            }

            // ------------------------------------------------
            // Ask for updated values
            // ------------------------------------------------

            const firstName =
                prompt(
                    "First Name:",
                    employee.first_name || ""
                );

            if (firstName === null) {
                return;
            }

            const lastName =
                prompt(
                    "Last Name:",
                    employee.last_name || ""
                );

            if (lastName === null) {
                return;
            }

            const email =
                prompt(
                    "Email:",
                    employee.email || ""
                );

            if (email === null) {
                return;
            }

            const phone =
                prompt(
                    "Phone Number (10 digits):",
                    employee.phone || ""
                );

            if (phone === null) {
                return;
            }

            const designation =
                prompt(
                    "Designation:",
                    employee.designation || ""
                );

            if (designation === null) {
                return;
            }

            const departmentId =
                prompt(
                    "Department ID:",
                    employee.department_id || ""
                );

            if (departmentId === null) {
                return;
            }

            const joiningDate =
                prompt(
                    "Joining Date (YYYY-MM-DD):",
                    employee.joining_date || ""
                );

            if (joiningDate === null) {
                return;
            }

            const employmentStatus =
                prompt(
                    "Employment Status:",
                    employee.employment_status || "Active"
                );

            if (employmentStatus === null) {
                return;
            }

            // ------------------------------------------------
            // Build update object
            // ------------------------------------------------

            const updateData = {

                first_name:
                    firstName.trim(),

                last_name:
                    lastName.trim(),

                email:
                    email.trim(),

                phone:
                    phone.trim() || null,

                department_id:
                    Number(
                        departmentId.trim()
                    ),

                designation:
                    designation.trim(),

                joining_date:
                    joiningDate.trim(),

                employment_status:
                    employmentStatus.trim()
            };

            // ------------------------------------------------
            // Validation
            // ------------------------------------------------

            if (!updateData.first_name) {
                alert(
                    "First Name is required."
                );
                return;
            }

            if (
                !namePattern.test(
                    updateData.first_name
                )
            ) {
                alert(
                    "First Name must contain characters only."
                );
                return;
            }

            if (!updateData.last_name) {
                alert(
                    "Last Name is required."
                );
                return;
            }

            if (
                !namePattern.test(
                    updateData.last_name
                )
            ) {
                alert(
                    "Last Name must contain characters only."
                );
                return;
            }

            if (!updateData.email) {
                alert(
                    "Email is required."
                );
                return;
            }

            if (
                updateData.phone &&
                !phonePattern.test(
                    updateData.phone
                )
            ) {
                alert(
                    "Phone number must contain exactly 10 digits."
                );
                return;
            }

            if (
                !updateData.department_id ||
                Number.isNaN(
                    updateData.department_id
                )
            ) {
                alert(
                    "Valid Department ID is required."
                );
                return;
            }

            if (!updateData.designation) {
                alert(
                    "Designation is required."
                );
                return;
            }

            if (
                !namePattern.test(
                    updateData.designation
                )
            ) {
                alert(
                    "Designation must contain characters only."
                );
                return;
            }

            if (!updateData.joining_date) {
                alert(
                    "Joining date is required."
                );
                return;
            }

            // ------------------------------------------------
            // Update API
            // ------------------------------------------------

            const updateResponse =
                await apiFetch(
                    `/employees/${employeeId}`,
                    {
                        method: "PUT",
                        body: JSON.stringify(
                            updateData
                        )
                    }
                );

            const result =
                await updateResponse
                    .json()
                    .catch(() => ({}));

            if (!updateResponse.ok) {

                throw new Error(
                    result.detail ||
                    "Unable to update employee."
                );
            }

            alert(
                "Employee updated successfully."
            );

            await loadEmployees();

        } catch (error) {

            console.error(error);

            alert(
                error.message ||
                "Unable to update employee."
            );
        }
    }

    // ========================================================
    // DELETE EMPLOYEE
    // ========================================================

    async function deleteEmployee(employeeId) {

        const confirmed =
            confirm(
                "Are you sure you want to delete this employee?"
            );

        if (!confirmed) {
            return;
        }

        try {

            const response =
                await apiFetch(
                    `/employees/${employeeId}`,
                    {
                        method: "DELETE"
                    }
                );

            const data =
                await response
                    .json()
                    .catch(() => ({}));

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Unable to delete employee."
                );
            }

            alert(
                "Employee deleted successfully."
            );

            await loadEmployees();

        } catch (error) {

            console.error(error);

            alert(
                error.message ||
                "Unable to delete employee."
            );
        }
    }

    // ========================================================
    // REFRESH
    // ========================================================

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            loadEmployees
        );
    }

    // ========================================================
    // HTML ESCAPE
    // ========================================================

    function escapeHtml(value) {

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

    // ========================================================
    // INITIAL LOAD
    // ========================================================

    loadEmployees();

});