// ============================================================
// DEPARTMENT MANAGEMENT
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    // --------------------------------------------------------
    // ELEMENTS
    // --------------------------------------------------------

    const addButton =
        document.getElementById("showAddDepartmentButton");

    const formSection =
        document.getElementById("departmentFormSection");

    const departmentForm =
        document.getElementById("departmentForm");

    const formTitle =
        document.getElementById("departmentFormTitle");

    const submitButton =
        document.getElementById("departmentSubmitButton");

    const cancelButton =
        document.getElementById("cancelDepartmentButton");

    const refreshButton =
        document.getElementById("refreshDepartmentsButton");

    const tableBody =
        document.getElementById("departmentTableBody");

    const message =
        document.getElementById("departmentFormMessage");

    const accessMessage =
        document.getElementById("departmentAccessMessage");

    const editIdInput =
        document.getElementById("departmentEditId");

    const nameInput =
        document.getElementById("departmentName");

    const descriptionInput =
        document.getElementById("departmentDescription");

    const statusInput =
        document.getElementById("departmentStatus");


    // --------------------------------------------------------
    // CURRENT USER ROLE
    // --------------------------------------------------------

    const role =
        typeof getRole === "function"
            ? getRole()
            : localStorage.getItem("role");


    // --------------------------------------------------------
    // ROLE CHECK
    // --------------------------------------------------------

    const isAdmin = role === "admin";


    // --------------------------------------------------------
    // ADMIN / HR ACCESS
    // --------------------------------------------------------

    if (!isAdmin) {

        if (addButton) {
            addButton.style.display = "none";
        }

        if (accessMessage) {
            accessMessage.textContent =
                "You have view-only access to departments.";
            accessMessage.className =
                "message";
        }
    }


    // --------------------------------------------------------
    // SHOW ADD DEPARTMENT FORM
    // --------------------------------------------------------

    if (addButton && formSection && isAdmin) {

        addButton.addEventListener("click", () => {

            resetDepartmentForm();

            formSection.style.display = "block";

            formSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            if (nameInput) {

                setTimeout(() => {
                    nameInput.focus();
                }, 300);
            }
        });
    }


    // --------------------------------------------------------
    // CANCEL
    // --------------------------------------------------------

    if (cancelButton && formSection) {

        cancelButton.addEventListener("click", () => {

            resetDepartmentForm();

            formSection.style.display = "none";
        });
    }


    // --------------------------------------------------------
    // RESET FORM
    // --------------------------------------------------------

    function resetDepartmentForm() {

        if (departmentForm) {
            departmentForm.reset();
        }

        if (editIdInput) {
            editIdInput.value = "";
        }

        if (formTitle) {
            formTitle.textContent =
                "Add New Department";
        }

        if (submitButton) {
            submitButton.textContent =
                "Create Department";
        }

        if (statusInput) {
            statusInput.value = "Active";
        }

        clearMessage();
    }


    // --------------------------------------------------------
    // OPEN EDIT FORM
    // --------------------------------------------------------

    function openEditForm(department) {

        if (!isAdmin) {
            return;
        }

        if (!formSection) {
            return;
        }

        if (editIdInput) {
            editIdInput.value =
                department.id;
        }

        if (nameInput) {
            nameInput.value =
                department.name || "";
        }

        if (descriptionInput) {
            descriptionInput.value =
                department.description || "";
        }

        if (statusInput) {
            statusInput.value =
                department.is_active || "Active";
        }

        if (formTitle) {
            formTitle.textContent =
                "Edit Department";
        }

        if (submitButton) {
            submitButton.textContent =
                "Update Department";
        }

        clearMessage();

        formSection.style.display = "block";

        formSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        if (nameInput) {

            setTimeout(() => {
                nameInput.focus();
            }, 300);
        }
    }


    // --------------------------------------------------------
    // LOAD DEPARTMENTS
    // --------------------------------------------------------

    async function loadDepartments() {

        if (!tableBody) {
            return;
        }

        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-table">
                    Loading departments...
                </td>
            </tr>
        `;

        try {

            const response =
                await apiFetch("/departments/");


            if (response.status === 401) {

                if (typeof logout === "function") {
                    logout();
                }

                return;
            }


            if (!response.ok) {

                const data =
                    await response
                        .json()
                        .catch(() => ({}));

                throw new Error(
                    data.detail ||
                    "Unable to load departments."
                );
            }


            const data =
                await response.json();


            const departments =
                Array.isArray(data)
                    ? data
                    : (data.departments || []);


            renderDepartments(departments);

        } catch (error) {

            console.error(error);

            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-table">
                        ${escapeHtml(error.message)}
                    </td>
                </tr>
            `;
        }
    }


    // --------------------------------------------------------
    // RENDER DEPARTMENTS
    // --------------------------------------------------------

    function renderDepartments(departments) {

        if (!departments.length) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-table">
                        No departments found.
                    </td>
                </tr>
            `;

            return;
        }


        tableBody.innerHTML = "";


        departments.forEach(department => {

            const row =
                document.createElement("tr");


            // ------------------------------------------------
            // STATUS
            // ------------------------------------------------

            const status =
                department.is_active || "Active";


            // ------------------------------------------------
            // ACTIONS
            // ------------------------------------------------

            let actionsHtml = "";


            if (isAdmin) {

                actionsHtml = `
                    <button
                        type="button"
                        class="edit-button small-button"
                        data-edit-id="${escapeHtml(department.id)}"
                    >
                        Edit
                    </button>

                    <button
                        type="button"
                        class="delete-button small-button"
                        data-delete-id="${escapeHtml(department.id)}"
                    >
                        Delete
                    </button>
                `;

            } else {

                actionsHtml = `
                    <span class="view-only-text">
                        View Only
                    </span>
                `;
            }


            // ------------------------------------------------
            // ROW
            // ------------------------------------------------

            row.innerHTML = `
                <td>
                    ${escapeHtml(department.id)}
                </td>

                <td>
                    ${escapeHtml(
                        department.name || "-"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        department.description || "-"
                    )}
                </td>

                <td>
                    <span class="${
                        status === "Active"
                            ? "status-active"
                            : "inactive-badge"
                    }">
                        ${escapeHtml(status)}
                    </span>
                </td>

                <td>
                    ${actionsHtml}
                </td>
            `;


            tableBody.appendChild(row);


            // ------------------------------------------------
            // EDIT BUTTON
            // ------------------------------------------------

            if (isAdmin) {

                const editButton =
                    row.querySelector(
                        "[data-edit-id]"
                    );


                if (editButton) {

                    editButton.addEventListener(
                        "click",
                        () => {

                            openEditForm(
                                department
                            );
                        }
                    );
                }
            }


            // ------------------------------------------------
            // DELETE BUTTON
            // ------------------------------------------------

            if (isAdmin) {

                const deleteButton =
                    row.querySelector(
                        "[data-delete-id]"
                    );


                if (deleteButton) {

                    deleteButton.addEventListener(
                        "click",
                        async () => {

                            const departmentId =
                                deleteButton.dataset.deleteId;

                            await deleteDepartment(
                                departmentId
                            );
                        }
                    );
                }
            }

        });
    }


    // --------------------------------------------------------
    // CREATE / UPDATE DEPARTMENT
    // --------------------------------------------------------

    if (departmentForm) {

        departmentForm.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();


                if (!isAdmin) {

                    showError(
                        "Only administrators can modify departments."
                    );

                    return;
                }


                const editId =
                    editIdInput
                        ? editIdInput.value.trim()
                        : "";


                const departmentData = {

                    name:
                        nameInput
                            ? nameInput.value.trim()
                            : "",

                    description:
                        descriptionInput
                            ? (
                                descriptionInput.value.trim() ||
                                null
                            )
                            : null,

                    is_active:
                        statusInput
                            ? statusInput.value
                            : "Active"
                };


                if (!departmentData.name) {

                    showError(
                        "Department name is required."
                    );

                    return;
                }


                // ------------------------------------------------
                // EDIT MODE
                // ------------------------------------------------

                const isEditMode =
                    editId !== "";


                if (isEditMode) {

                    await updateDepartment(
                        editId,
                        departmentData
                    );

                }


                // ------------------------------------------------
                // CREATE MODE
                // ------------------------------------------------

                else {

                    await createDepartment(
                        departmentData
                    );
                }

            }
        );
    }


    // --------------------------------------------------------
    // CREATE DEPARTMENT
    // --------------------------------------------------------

    async function createDepartment(
        departmentData
    ) {

        showMessage(
            "Creating department...",
            "message"
        );


        try {

            const response =
                await apiFetch(
                    "/departments/",
                    {
                        method: "POST",
                        body:
                            JSON.stringify(
                                departmentData
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
                    "Unable to create department."
                );
            }


            showMessage(
                "Department created successfully.",
                "message success-message"
            );


            await loadDepartments();


            setTimeout(() => {

                if (formSection) {
                    formSection.style.display =
                        "none";
                }

                resetDepartmentForm();

            }, 1000);


        } catch (error) {

            console.error(error);

            showError(
                error.message ||
                "Unable to create department."
            );
        }
    }


    // --------------------------------------------------------
    // UPDATE DEPARTMENT
    // --------------------------------------------------------

    async function updateDepartment(
        departmentId,
        departmentData
    ) {

        showMessage(
            "Updating department...",
            "message"
        );


        try {

            const response =
                await apiFetch(
                    `/departments/${departmentId}`,
                    {
                        method: "PUT",
                        body:
                            JSON.stringify(
                                departmentData
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
                    "Unable to update department."
                );
            }


            showMessage(
                "Department updated successfully.",
                "message success-message"
            );


            await loadDepartments();


            setTimeout(() => {

                if (formSection) {
                    formSection.style.display =
                        "none";
                }

                resetDepartmentForm();

            }, 1000);


        } catch (error) {

            console.error(error);

            showError(
                error.message ||
                "Unable to update department."
            );
        }
    }


    // --------------------------------------------------------
    // DELETE DEPARTMENT
    // --------------------------------------------------------

    async function deleteDepartment(
        departmentId
    ) {

        if (!isAdmin) {
            return;
        }


        const confirmed =
            confirm(
                "Are you sure you want to delete this department?"
            );


        if (!confirmed) {
            return;
        }


        try {

            const response =
                await apiFetch(
                    `/departments/${departmentId}`,
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
                    "Unable to delete department."
                );
            }


            alert(
                "Department deleted successfully."
            );


            await loadDepartments();


        } catch (error) {

            console.error(error);

            alert(
                error.message ||
                "Unable to delete department."
            );
        }
    }


    // --------------------------------------------------------
    // REFRESH
    // --------------------------------------------------------

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            loadDepartments
        );
    }


    // --------------------------------------------------------
    // MESSAGE HELPERS
    // --------------------------------------------------------

    function showMessage(
        text,
        className
    ) {

        if (!message) {
            return;
        }

        message.textContent =
            text;

        message.className =
            className;
    }


    function showError(
        text
    ) {

        showMessage(
            text,
            "message error-message"
        );
    }


    function clearMessage() {

        if (!message) {
            return;
        }

        message.textContent =
            "";

        message.className =
            "message";
    }


    // --------------------------------------------------------
    // HTML ESCAPE
    // --------------------------------------------------------

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


    // --------------------------------------------------------
    // INITIAL LOAD
    // --------------------------------------------------------

    loadDepartments();

});