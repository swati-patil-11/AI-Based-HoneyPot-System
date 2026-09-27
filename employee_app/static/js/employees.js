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

    // --------------------------------------------------------
    // SHOW ADD EMPLOYEE FORM
    // --------------------------------------------------------

    if (addButton && formSection) {

        addButton.addEventListener("click", () => {

            formSection.style.display = "block";

            formSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            const firstField = document.getElementById("employeeId");

            if (firstField) {
                setTimeout(() => {
                    firstField.focus();
                }, 300);
            }
        });
    }

    // --------------------------------------------------------
    // CANCEL
    // --------------------------------------------------------

    if (cancelButton && formSection) {

        cancelButton.addEventListener("click", () => {

            employeeForm.reset();

            formSection.style.display = "none";

            if (message) {
                message.textContent = "";
                message.className = "message";
            }
        });
    }

    // --------------------------------------------------------
    // LOAD EMPLOYEES
    // --------------------------------------------------------

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

            const response = await apiFetch("/employees/");

            if (response.status === 401) {
                logout();
                return;
            }

            if (!response.ok) {

                const data = await response.json().catch(() => ({}));

                throw new Error(
                    data.detail || "Unable to load employees."
                );
            }

            const data = await response.json();

            const employees = Array.isArray(data)
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

    // --------------------------------------------------------
    // RENDER EMPLOYEES
    // --------------------------------------------------------

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

            const row = document.createElement("tr");

            const fullName =
                `${employee.first_name || ""} ${employee.last_name || ""}`.trim();

            row.innerHTML = `
                <td>${escapeHtml(employee.id)}</td>

                <td>
                    ${escapeHtml(employee.employee_id || "-")}
                </td>

                <td>
                    ${escapeHtml(fullName || "-")}
                </td>

                <td>
                    ${escapeHtml(employee.email || "-")}
                </td>

                <td>
                    ${escapeHtml(employee.department_id ?? "-")}
                </td>

                <td>
                    ${escapeHtml(employee.designation || "-")}
                </td>

                <td>
                    ${escapeHtml(employee.employment_status || "-")}
                </td>

                <td>
    ${
        getRole() === "admin"
            ? `
                <button
                    type="button"
                    class="delete-button small-button"
                    data-delete-id="${employee.id}"
                >
                    Delete
                </button>
              `
            : `
                <span class="view-only-action">
                    View Only
                </span>
              `
    }
</td>
            `;

            tableBody.appendChild(row);
        });

        // Attach delete events.
        tableBody
            .querySelectorAll("[data-delete-id]")
            .forEach(button => {

                button.addEventListener("click", async () => {

                    const employeeId = button.dataset.deleteId;

                    await deleteEmployee(employeeId);
                });
            });
    }

    // --------------------------------------------------------
    // CREATE EMPLOYEE
    // --------------------------------------------------------

    if (employeeForm) {

        employeeForm.addEventListener("submit", async (event) => {

            event.preventDefault();

            if (message) {
                message.textContent = "Creating employee...";
                message.className = "message";
            }

            const employeeData = {

                employee_id:
                    document.getElementById("employeeId").value.trim(),

                first_name:
                    document.getElementById("firstName").value.trim(),

                last_name:
                    document.getElementById("lastName").value.trim(),

                email:
                    document.getElementById("email").value.trim(),

                phone:
                    document.getElementById("phone").value.trim() || null,

                department_id:
                    Number(document.getElementById("departmentId").value),

                designation:
                    document.getElementById("designation").value.trim(),

                joining_date:
                    document.getElementById("joiningDate").value,

                employment_status:
                    document.getElementById("employmentStatus").value
            };

            try {

                const response = await apiFetch("/employees/", {
                    method: "POST",
                    body: JSON.stringify(employeeData)
                });

                const data = await response.json().catch(() => ({}));

                if (!response.ok) {

                    throw new Error(
                        data.detail || "Unable to create employee."
                    );
                }

                if (message) {

                    message.textContent =
                        "Employee created successfully.";

                    message.className =
                        "message success-message";
                }

                employeeForm.reset();

                await loadEmployees();

                setTimeout(() => {

                    formSection.style.display = "none";

                    if (message) {
                        message.textContent = "";
                        message.className = "message";
                    }

                }, 1200);

            } catch (error) {

                console.error(error);

                if (message) {

                    message.textContent =
                        error.message || "Unable to create employee.";

                    message.className =
                        "message error-message";
                }
            }
        });
    }

    // --------------------------------------------------------
    // DELETE EMPLOYEE
    // --------------------------------------------------------

    async function deleteEmployee(employeeId) {

        const confirmed = confirm(
            "Are you sure you want to delete this employee?"
        );

        if (!confirmed) {
            return;
        }

        try {

            const response = await apiFetch(
                `/employees/${employeeId}`,
                {
                    method: "DELETE"
                }
            );

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {

                throw new Error(
                    data.detail || "Unable to delete employee."
                );
            }

            alert("Employee deleted successfully.");

            await loadEmployees();

        } catch (error) {

            console.error(error);

            alert(
                error.message || "Unable to delete employee."
            );
        }
    }

    // --------------------------------------------------------
    // REFRESH
    // --------------------------------------------------------

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            loadEmployees
        );
    }

    // --------------------------------------------------------
    // HTML ESCAPE
    // --------------------------------------------------------

    function escapeHtml(value) {

        if (value === null || value === undefined) {
            return "";
        }

        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initial load.
    loadEmployees();
});