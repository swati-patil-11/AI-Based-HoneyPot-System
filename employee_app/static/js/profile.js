// =========================================================
// MY PROFILE UI
// =========================================================


// ---------------------------------------------------------
// Detect Profile Page
// ---------------------------------------------------------

const profileContent =
    document.getElementById(
        "profileContent"
    );


if (profileContent) {

    initializeProfilePage();

}


// ---------------------------------------------------------
// Initialize Profile Page
// ---------------------------------------------------------

function initializeProfilePage() {

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
    // Only employees use My Profile
    // -----------------------------------------------------

    if (role !== "employee") {

        profileContent.style.display =
            "block";

        document.getElementById(
            "profileAccessDenied"
        ).style.display =
            "block";

        return;

    }


    // -----------------------------------------------------
    // Show profile
    // -----------------------------------------------------

    profileContent.style.display =
        "block";


    const welcome =
        document.getElementById(
            "profilePageWelcome"
        );


    if (welcome) {

        welcome.textContent =
            "Welcome, " +
            username;

    }


    loadMyProfile(token);


    // -----------------------------------------------------
    // Form submit
    // -----------------------------------------------------

    const profileForm =
        document.getElementById(
            "profileForm"
        );


    if (profileForm) {

        profileForm.addEventListener(
            "submit",
            updateMyProfile
        );

    }

}


// =========================================================
// LOAD PROFILE
// =========================================================

async function loadMyProfile(token) {

    try {

        const response =
            await fetch(
                "/employees/me",
                {

                    headers: {

                        "Authorization":
                            "Bearer " + token

                    }

                }
            );


        if (response.status === 401) {

            logoutFromProfile();

            return;

        }


        const data =
            await response.json();


        if (!response.ok) {

            showProfileMessage(
                data.detail ||
                "Unable to load profile."
            );

            return;

        }


        const employee =
            data.employee;


        // -------------------------------------------------
        // Display information
        // -------------------------------------------------

        document.getElementById(
            "profileEmployeeId"
        ).textContent =
            employee.employee_id;


        document.getElementById(
            "profileUsername"
        ).textContent =
            localStorage.getItem(
                "username"
            );


        document.getElementById(
            "profileEmail"
        ).textContent =
            employee.email;


        document.getElementById(
            "profileDesignation"
        ).textContent =
            employee.designation;


        document.getElementById(
            "profileDepartment"
        ).textContent =
            employee.department_id;


        document.getElementById(
            "profileJoiningDate"
        ).textContent =
            formatProfileDate(
                employee.joining_date
            );


        document.getElementById(
            "profileEmploymentStatus"
        ).textContent =
            employee.employment_status;


        // -------------------------------------------------
        // Editable fields
        // -------------------------------------------------

        document.getElementById(
            "profileFirstName"
        ).value =
            employee.first_name;


        document.getElementById(
            "profileLastName"
        ).value =
            employee.last_name;


        document.getElementById(
            "profilePhone"
        ).value =
            employee.phone || "";


    } catch (error) {

        console.error(
            "Profile loading error:",
            error
        );


        showProfileMessage(
            "Unable to connect to server."
        );

    }

}


// =========================================================
// UPDATE PROFILE
// =========================================================

async function updateMyProfile(event) {

    event.preventDefault();


    const token =
        localStorage.getItem(
            "access_token"
        );


    const button =
        document.getElementById(
            "updateProfileButton"
        );


    const firstName =
        document.getElementById(
            "profileFirstName"
        ).value.trim();


    const lastName =
        document.getElementById(
            "profileLastName"
        ).value.trim();


    const phone =
        document.getElementById(
            "profilePhone"
        ).value.trim();


    if (!firstName) {

        showProfileMessage(
            "First name is required."
        );

        return;

    }


    if (!lastName) {

        showProfileMessage(
            "Last name is required."
        );

        return;

    }


    button.disabled = true;


    showProfileMessage(
        "Saving changes..."
    );


    try {

        const response =
            await fetch(
                "/employees/me",
                {

                    method: "PUT",

                    headers: {

                        "Content-Type":
                            "application/json",

                        "Authorization":
                            "Bearer " + token

                    },

                    body:
                        JSON.stringify({

                            first_name:
                                firstName,

                            last_name:
                                lastName,

                            phone:
                                phone || null

                        })

                }
            );


        const data =
            await response.json();


        if (response.status === 401) {

            logoutFromProfile();

            return;

        }


        if (!response.ok) {

            showProfileMessage(
                data.detail ||
                "Unable to update profile."
            );

            return;

        }


        showProfileMessage(
            "Profile updated successfully."
        );


        // Refresh displayed information

        const employee =
            data.employee;


        document.getElementById(
            "profileEmployeeId"
        ).textContent =
            employee.employee_id;


        document.getElementById(
            "profileEmail"
        ).textContent =
            employee.email;


        document.getElementById(
            "profileDesignation"
        ).textContent =
            employee.designation;


        document.getElementById(
            "profileDepartment"
        ).textContent =
            employee.department_id;


        document.getElementById(
            "profileJoiningDate"
        ).textContent =
            formatProfileDate(
                employee.joining_date
            );


        document.getElementById(
            "profileEmploymentStatus"
        ).textContent =
            employee.employment_status;


    } catch (error) {

        console.error(
            "Profile update error:",
            error
        );


        showProfileMessage(
            "Unable to connect to server."
        );

    } finally {

        button.disabled = false;

    }

}


// =========================================================
// PROFILE MESSAGE
// =========================================================

function showProfileMessage(message) {

    const element =
        document.getElementById(
            "profileFormMessage"
        );


    if (element) {

        element.textContent =
            message;

    }

}


// =========================================================
// FORMAT DATE
// =========================================================

function formatProfileDate(
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


// =========================================================
// LOGOUT
// =========================================================

function logoutFromProfile() {

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