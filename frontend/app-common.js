/* =========================================
   MEETMIND AI - SHARED STORAGE
========================================= */

(function () {
    "use strict";

    const MEETINGS_KEY = "meetMindMeetings";
    const DATABASE_NAME = "MeetMindDatabase";
    const STORE_NAME = "meetingFiles";

    /* =========================================
       MEETING INFORMATION - LOCAL STORAGE
    ========================================= */

    // Read saved meeting information.
    function readMeetings() {
        try {
            const saved = localStorage.getItem(MEETINGS_KEY);

            if (!saved) {
                return [];
            }

            const meetings = JSON.parse(saved);

            return Array.isArray(meetings) ? meetings : [];
        } catch (error) {
            console.error("Could not read meetings:", error);
            return [];
        }
    }

    // Save meeting information.
    function writeMeetings(meetings) {
        if (!Array.isArray(meetings)) {
            throw new TypeError("Meetings must be an array.");
        }

        localStorage.setItem(
            MEETINGS_KEY,
            JSON.stringify(meetings)
        );
    }

    /* =========================================
       INDEXEDDB - DATABASE CONNECTION
    ========================================= */

    // Open or create the IndexedDB database.
    function openDatabase() {
        return new Promise(function (resolve, reject) {
            if (!window.indexedDB) {
                reject(new Error("IndexedDB is not supported."));
                return;
            }

            const request = indexedDB.open(DATABASE_NAME);

            request.onupgradeneeded = function (event) {
                const db = event.target.result;

                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, {
                        keyPath: "id"
                    });
                }
            };

            request.onsuccess = function () {
                const db = request.result;

                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.close();

                    reject(new Error(
                        "The meeting file store is missing. " +
                        "Check the existing IndexedDB setup."
                    ));

                    return;
                }

                resolve(db);
            };

            request.onerror = function () {
                reject(
                    request.error ||
                    new Error("Could not open the database.")
                );
            };

            request.onblocked = function () {
                console.warn(
                    "Database opening is blocked by another open page. " +
                    "Close other MEETMIND AI tabs and try again."
                );
            };
        });
    }

    /* =========================================
       SAVE UPLOADED FILE
    ========================================= */

    async function saveFile(id, file) {
        if (id === undefined || id === null || String(id) === "") {
            throw new Error("A valid meeting ID is required to save a file.");
        }

        if (!(file instanceof Blob)) {
            throw new TypeError("A valid uploaded file is required.");
        }

        const meetingId = String(id);
        const db = await openDatabase();

        return new Promise(function (resolve, reject) {
            let transaction;

            try {
                transaction = db.transaction(
                    [STORE_NAME],
                    "readwrite"
                );

                const store = transaction.objectStore(STORE_NAME);

                const record = {
                    id: meetingId,
                    file: file,
                    fileName: file.name || "meeting-file",
                    fileType: file.type || "",
                    savedAt: new Date().toISOString()
                };

                /*
                 * Support both IndexedDB store configurations:
                 *
                 * 1. Inline key: keyPath = "id"
                 *    Store.put(record)
                 *
                 * 2. Out-of-line key: no keyPath
                 *    Store.put(record, meetingId)
                 */
                if (store.keyPath === null) {
                    store.put(record, meetingId);
                } else {
                    store.put(record);
                }
            } catch (error) {
                db.close();
                reject(error);
                return;
            }

            transaction.oncomplete = function () {
                db.close();
                resolve(true);
            };

            transaction.onerror = function () {
                db.close();

                reject(
                    transaction.error ||
                    new Error("Could not save the uploaded file.")
                );
            };

            transaction.onabort = function () {
                db.close();

                reject(
                    transaction.error ||
                    new Error("File saving was cancelled.")
                );
            };
        });
    }

    /* =========================================
       RETRIEVE UPLOADED FILE
    ========================================= */

    async function getFile(id) {
        if (id === undefined || id === null || String(id) === "") {
            throw new Error("A valid meeting ID is required to retrieve a file.");
        }

        const meetingId = String(id);
        const db = await openDatabase();

        return new Promise(function (resolve, reject) {
            let transaction;

            try {
                transaction = db.transaction(
                    [STORE_NAME],
                    "readonly"
                );

                const store = transaction.objectStore(STORE_NAME);
                const request = store.get(meetingId);

                request.onsuccess = function () {
                    resolve(request.result || null);
                };

                request.onerror = function () {
                    reject(
                        request.error ||
                        new Error("Could not retrieve the uploaded file.")
                    );
                };

                transaction.oncomplete = function () {
                    db.close();
                };

                transaction.onerror = function () {
                    db.close();
                };

                transaction.onabort = function () {
                    db.close();
                };
            } catch (error) {
                db.close();
                reject(error);
            }
        });
    }

    /* =========================================
       DELETE UPLOADED FILE
    ========================================= */

    async function deleteFile(id) {
        if (id === undefined || id === null || String(id) === "") {
            throw new Error("A valid meeting ID is required to delete a file.");
        }

        const meetingId = String(id);
        const db = await openDatabase();

        return new Promise(function (resolve, reject) {
            let transaction;

            try {
                transaction = db.transaction(
                    [STORE_NAME],
                    "readwrite"
                );

                const store = transaction.objectStore(STORE_NAME);
                store.delete(meetingId);

                transaction.oncomplete = function () {
                    db.close();
                    resolve(true);
                };

                transaction.onerror = function () {
                    db.close();

                    reject(
                        transaction.error ||
                        new Error("Could not delete the uploaded file.")
                    );
                };

                transaction.onabort = function () {
                    db.close();

                    reject(
                        transaction.error ||
                        new Error("File deletion was cancelled.")
                    );
                };
            } catch (error) {
                db.close();
                reject(error);
            }
        });
    }

    /* =========================================
       HTML ESCAPING
    ========================================= */

    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[char];
        });
    }

    /* =========================================
       SHARED MEETMIND API
    ========================================= */

    window.MeetMind = Object.assign(window.MeetMind || {}, {
        readMeetings: readMeetings,
        writeMeetings: writeMeetings,
        saveFile: saveFile,
        getFile: getFile,
        deleteFile: deleteFile,
        escapeHTML: escapeHTML
    });

})();


/* =========================================
   SHARED PROFILE NAME AND AVATAR
========================================= */

document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const SETTINGS_KEY = "meetmindDashboardSettings";

    function updateProfile() {
        let profileName = "My Workspace";

        try {
            const settings = JSON.parse(
                localStorage.getItem(SETTINGS_KEY) || "{}"
            );

            profileName =
                settings.displayName ||
                settings.profileName ||
                settings.name ||
                profileName;
        } catch (error) {
            console.error("Could not load profile settings:", error);
        }

        profileName = String(profileName).trim() || "My Workspace";

        const initials = profileName
            .split(/\s+/)
            .map(function (word) {
                return word.charAt(0);
            })
            .join("")
            .substring(0, 2)
            .toUpperCase();

        // Dashboard profile name
        const profileButton = document.getElementById("profileButton");

        if (profileButton) {
            const nameElement = profileButton.querySelector(
                "span:not(.avatar):not(.profile-chevron)"
            );

            if (nameElement) {
                nameElement.textContent = profileName;
            }

            profileButton.setAttribute("aria-label", profileName);
        }

        // Meetings and History profile name
        document.querySelectorAll("#headerProfileName").forEach(
            function (element) {
                element.textContent = profileName;
            }
        );

        // Update avatar initials on every page
        document.querySelectorAll(
            ".avatar, #headerAvatar, #profileAvatar, " +
            ".profile-avatar, [data-profile-avatar]"
        ).forEach(function (element) {
            element.textContent = initials || "U";
        });
    }

    updateProfile();

    // Update automatically when settings change in another tab
    window.addEventListener("storage", function (event) {
        if (event.key === SETTINGS_KEY) {
            updateProfile();
        }
    });
});

/* =========================================
   SHARED LOGOUT HANDLER
========================================= */

document.addEventListener("click", async function (event) {
    const logoutLink = event.target.closest("#logoutLink");

    if (!logoutLink) {
        return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();

    const confirmed = confirm("Are you sure you want to log out?");

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch("/api/auth/logout", {
            method: "POST",
            credentials: "same-origin"
        });

        if (!response.ok) {
            throw new Error("Logout request failed.");
        }

        // Clear account-specific local storage
        localStorage.removeItem("meetMindMeetings");
        localStorage.removeItem("meetmindDashboardSettings");

        // Clear uploaded files from IndexedDB
        await new Promise(function (resolve) {
            const request = indexedDB.open("MeetMindDatabase");

            request.onsuccess = function () {
                const db = request.result;

                if (!db.objectStoreNames.contains("meetingFiles")) {
                    db.close();
                    resolve();
                    return;
                }

                const transaction = db.transaction(
                    ["meetingFiles"],
                    "readwrite"
                );

                transaction.objectStore("meetingFiles").clear();

                transaction.oncomplete = function () {
                    db.close();
                    resolve();
                };

                transaction.onerror = function () {
                    db.close();
                    resolve();
                };

                transaction.onabort = function () {
                    db.close();
                    resolve();
                };
            };

            request.onerror = function () {
                resolve();
            };
        });

        window.location.replace("/");

    } catch (error) {
        console.error("Logout error:", error);
        alert("Could not log out. Please try again.");
    }
}, true);