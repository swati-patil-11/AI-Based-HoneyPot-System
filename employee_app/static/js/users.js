// ============================================================
// User Management
// Admin only
// ============================================================


document.addEventListener("DOMContentLoaded", function () {

    const role = localStorage.getItem("role");
    const token = localStorage.getItem("access_token");

    // --------------------------------------------------------
    // Security check
    // --------------------------------------------------------

    if (!token) {
        window.location.href = "/";
        return;
    }

    if (role !== "admin") {
        window.location.href = "/dashboard";
        return;
    }


    loadUsers();


    const createUserForm =
        document.getElementById("createUserForm");

    if (createUserForm) {

        createUserForm.addEventListener(
            "submit",
            createUser
        );
    }


    const refreshButton =
        document.getElementById("refreshUsers");

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            loadUsers
        );
    }
});


// ============================================================
// Load users
// ============================================================

async function loadUsers() {

    const token =
        localStorage.getItem("access_token");

    const loading =
        document.getElementById("usersLoading");

    const tableBody =
        document.getElementById("usersTableBody");


    if (loading) {
        loading.style.display = "block";
    }


    try {

        const response = await fetch(
            "/users/",
            {
                headers: {
                    "Authorization":
                        `Bearer ${token}`
                }
            }
        );


        if (!response.ok) {

            const data = await response.json();

            throw new Error(
                data.detail || "Unable to load users."
            );
        }


        const users = await response.json();


        tableBody.innerHTML = "";


        users.forEach(function (user) {

            const row =
                document.createElement("tr");


            const status =
                user.is_active
                    ? "Active"
                    : "Inactive";


            const statusClass =
                user.is_active
                    ? "status-active"
                    : "status-inactive";


            row.innerHTML = `

                <td>
                    ${user.id}
                </td>

                <td>
                    <strong>
                        ${escapeHtml(user.username)}
                    </strong>
                </td>

                <td>
                    ${escapeHtml(user.email)}
                </td>

                <td>
                    ${escapeHtml(
                        user.role.toUpperCase()
                    )}
                </td>

                <td>
                    <span class="${statusClass}">
                        ${status}
                    </span>
                </td>

                <td>

                    <button
                        class="secondary-button small-button"
                        onclick="toggleUserStatus(${user.id})"
                    >
                        ${user.is_active
                            ? "Deactivate"
                            : "Activate"}
                    </button>

                    <button
                        class="secondary-button small-button"
                        onclick="resetUserPassword(
                            ${user.id},
                            '${escapeJs(user.username)}'
                        )"
                    >
                        Reset Password
                    </button>

                </td>

            `;


            tableBody.appendChild(row);
        });


    } catch (error) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="6">
                    ${escapeHtml(error.message)}
                </td>
            </tr>
        `;

    } finally {

        if (loading) {
            loading.style.display = "none";
        }
    }
}


// ============================================================
// Create user
// ============================================================

async function createUser(event) {

    event.preventDefault();


    const username =
        document.getElementById(
            "newUsername"
        ).value.trim();


    const email =
        document.getElementById(
            "newEmail"
        ).value.trim();


    const password =
        document.getElementById(
            "newPassword"
        ).value;


    const role =
        document.getElementById(
            "newRole"
        ).value;


    const message =
        document.getElementById(
            "userMessage"
        );


    try {

        const token =
            localStorage.getItem(
                "access_token"
            );


        const response =
            await fetch(
                "/users/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            `Bearer ${token}`
                    },

                    body: JSON.stringify({
                        username,
                        email,
                        password,
                        role
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to create user."
            );
        }


        message.textContent =
            "User created successfully.";

        message.className =
            "message success-message";


        document
            .getElementById(
                "createUserForm"
            )
            .reset();


        await loadUsers();


    } catch (error) {

        message.textContent =
            error.message;

        message.className =
            "message error-message";
    }
}


// ============================================================
// Activate / deactivate user
// ============================================================

async function toggleUserStatus(userId) {

    const token =
        localStorage.getItem(
            "access_token"
        );


    try {

        const response =
            await fetch(
                `/users/${userId}/status`,
                {
                    method: "PUT",

                    headers: {
                        "Authorization":
                            `Bearer ${token}`
                    }
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to update user status."
            );
        }


        await loadUsers();


    } catch (error) {

        alert(error.message);
    }
}


// ============================================================
// Reset password
// ============================================================

async function resetUserPassword(
    userId,
    username
) {

    const newPassword =
        prompt(
            `Enter new password for ${username}:`
        );


    if (!newPassword) {
        return;
    }


    if (newPassword.length < 6) {

        alert(
            "Password must be at least 6 characters long."
        );

        return;
    }


    const token =
        localStorage.getItem(
            "access_token"
        );


    try {

        const response =
            await fetch(
                `/users/${userId}/password`,
                {
                    method: "PUT",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            `Bearer ${token}`
                    },

                    body: JSON.stringify({
                        password: newPassword
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to reset password."
            );
        }


        alert(
            "Password reset successfully."
        );


    } catch (error) {

        alert(error.message);
    }
}


// ============================================================
// Security helpers
// ============================================================

function escapeHtml(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function escapeJs(value) {

    return String(value)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'");
}