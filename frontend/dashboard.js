
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // =========================================
    // 1. GET HTML ELEMENTS
    // =========================================

    const meetingFile = document.getElementById("meetingFile");
    const filePicker = document.getElementById("filePicker");
    const meetingUrl = document.getElementById("meetingUrl");
    const analyzeButton = document.getElementById("analyzeButton");

    const fileInfo = document.getElementById("fileInfo");

    const selectedFilePreview =
        document.getElementById("selectedFilePreview");

    const selectedFileIcon =
        document.getElementById("selectedFileIcon");

    const selectedFileName =
        document.getElementById("selectedFileName");

    const selectedFileMeta =
        document.getElementById("selectedFileMeta");

    const selectedFileType =
        document.getElementById("selectedFileType");

    const urlInfo = document.getElementById("urlInfo");
    const analysisMessage = document.getElementById("analysisMessage");

    const meetingList = document.getElementById("meetingList");
    const emptyRecent = document.getElementById("emptyRecent");
    const dashboardSearch = document.getElementById("dashboardSearch");

    const themeToggle = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeToggleIcon");

    const notificationButton =
        document.getElementById("notificationButton");

    const profileButton =
        document.getElementById("profileButton");

    // =========================================
    // 2. SVG ICONS
    // =========================================

    const ICONS = {
        moon: `
            <svg viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="1.8"
                stroke-linecap="round" stroke-linejoin="round"
                aria-hidden="true">
                <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5
                    8.5 8.5 0 1 0 20.5 14.2Z"/>
            </svg>
        `,

        sun: `
            <svg viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="1.8"
                stroke-linecap="round" stroke-linejoin="round"
                aria-hidden="true">
                <circle cx="12" cy="12" r="4"/>
                <path d="M12 2v2"/>
                <path d="M12 20v2"/>
                <path d="M4.93 4.93l1.42 1.42"/>
                <path d="M17.65 17.65l1.42 1.42"/>
                <path d="M2 12h2"/>
                <path d="M20 12h2"/>
                <path d="M4.93 19.07l1.42-1.42"/>
                <path d="M17.65 6.35l1.42-1.42"/>
            </svg>
        `
    };

    // =========================================
    // 3. LIGHT / DARK THEME
    // =========================================

    const THEME_KEY = "meetmind-auth-theme";
    const OLD_THEME_KEY = "meetingAITheme";

    function readSavedTheme() {
        try {
            return (
                localStorage.getItem(THEME_KEY) ||
                localStorage.getItem(OLD_THEME_KEY) ||
                "light"
            );
        } catch (error) {
            return "light";
        }
    }

    function applyTheme(theme, savePreference = false) {
        const isDark = theme === "dark";

        document.body.classList.toggle("dark-mode", isDark);
        document.documentElement.classList.toggle("dark-mode", isDark);

        if (themeIcon) {
            themeIcon.innerHTML = isDark ? ICONS.sun : ICONS.moon;
        }

        if (themeToggle) {
            const label = isDark
                ? "Switch to light mode"
                : "Switch to dark mode";

            themeToggle.setAttribute("aria-label", label);
            themeToggle.setAttribute("title", label);
            themeToggle.setAttribute("aria-pressed", String(isDark));
        }

        if (savePreference) {
            try {
                localStorage.setItem(
                    THEME_KEY,
                    isDark ? "dark" : "light"
                );

                localStorage.setItem(
                    OLD_THEME_KEY,
                    isDark ? "dark" : "light"
                );
            } catch (error) {
                console.warn("Could not save theme preference:", error);
            }
        }
    }

    applyTheme(readSavedTheme());

    if (themeToggle && !themeToggle.dataset.themeHandlerAttached) {
        themeToggle.dataset.themeHandlerAttached = "true";

        themeToggle.addEventListener("click", function (event) {
            event.preventDefault();

            const isDark =
                document.body.classList.contains("dark-mode");

            applyTheme(isDark ? "light" : "dark", true);
        });
    }

    // =========================================
    // 4. MEETING STORAGE
    // =========================================

    const STORAGE_KEY = "meetMindMeetings";
    const DATABASE_NAME = "MeetMindDatabase";
    const STORE_NAME = "meetingFiles";

    if (!window.MeetMind) {
        window.MeetMind = {};
    }

    const MeetMind = window.MeetMind;

    if (typeof MeetMind.readMeetings !== "function") {
        MeetMind.readMeetings = function () {
            try {
                const saved = localStorage.getItem(STORAGE_KEY);
                const meetings = saved ? JSON.parse(saved) : [];

                return Array.isArray(meetings) ? meetings : [];
            } catch (error) {
                console.error("Could not read meeting history:", error);
                return [];
            }
        };
    }

    if (typeof MeetMind.writeMeetings !== "function") {
        MeetMind.writeMeetings = function (meetings) {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(meetings)
            );
        };
    }

    if (typeof MeetMind.escapeHTML !== "function") {
        MeetMind.escapeHTML = function (value) {
            return String(value ?? "").replace(/[&<>"']/g, function (char) {
                const entities = {
                    "&": "&amp;",
                    "<": "&lt;",
                    ">": "&gt;",
                    '"': "&quot;",
                    "'": "&#39;"
                };

                return entities[char];
            });
        };
    }

    // Fallback IndexedDB file storage.
    if (typeof MeetMind.saveFile !== "function") {
        MeetMind.saveFile = function (id, file) {
            return new Promise(function (resolve, reject) {
                if (!window.indexedDB) {
                    reject(new Error("IndexedDB is not available."));
                    return;
                }

                const request = indexedDB.open(DATABASE_NAME, 1);

                request.onupgradeneeded = function () {
                    const database = request.result;

                    if (!database.objectStoreNames.contains(STORE_NAME)) {
                        database.createObjectStore(STORE_NAME);
                    }
                };

                request.onerror = function () {
                    reject(
                        request.error ||
                        new Error("Could not open file storage.")
                    );
                };

                request.onsuccess = function () {
                    const database = request.result;
                    let transaction;

                    try {
                        transaction = database.transaction(
                            STORE_NAME,
                            "readwrite"
                        );

                        const store = transaction.objectStore(STORE_NAME);

                        if (store.keyPath === null) {
                            store.put(file, String(id));
                        } else if (store.keyPath === "id") {
                            store.put({
                                id: String(id),
                                file: file
                            });
                        } else if (typeof store.keyPath === "string") {
                            const record = { file: file };
                            record[store.keyPath] = String(id);
                            store.put(record);
                        } else {
                            throw new Error(
                                "Unsupported IndexedDB key configuration."
                            );
                        }

                        transaction.oncomplete = function () {
                            database.close();
                            resolve();
                        };

                        transaction.onerror = function () {
                            const error = transaction.error;
                            database.close();

                            reject(
                                error ||
                                new Error("Could not save the uploaded file.")
                            );
                        };

                        transaction.onabort = function () {
                            const error = transaction.error;
                            database.close();

                            reject(
                                error ||
                                new Error("File saving was cancelled.")
                            );
                        };
                    } catch (error) {
                        database.close();
                        reject(error);
                    }
                };
            });
        };
    }

    // =========================================
    // 5. HELPER FUNCTIONS
    // =========================================

    function showMessage(element, message, type = "") {
        if (!element) return;

        element.textContent = message;
        element.className = "input-feedback";

        if (type) {
            element.classList.add(type);
        }
    }

    function getExtension(filename) {
        const parts = String(filename).split(".");

        return parts.length > 1
            ? parts.pop().toLowerCase()
            : "";
    }

    function getMeetingType(filename) {
        const extension = getExtension(filename);

        if (["mp4", "webm", "ogg", "mov", "avi"].includes(extension)) {
            return "Video";
        }

        if (["mp3", "wav", "m4a"].includes(extension)) {
            return "Audio";
        }

        if (extension === "pdf") {
            return "PDF";
        }

        if (["doc", "docx"].includes(extension)) {
            return "Document";
        }

        if (["jpg", "jpeg", "png"].includes(extension)) {
            return "Image";
        }

        return "File";
    }

    function isValidURL(value) {
        try {
            const parsedURL = new URL(value);

            return (
                (parsedURL.protocol === "https:" ||
                    parsedURL.protocol === "http:") &&
                Boolean(parsedURL.hostname)
            );
        } catch (error) {
            return false;
        }
    }

    function getMeetingIcon(type) {
        switch (type) {
            case "Video":
                return {
                    icon: `
                        <svg viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="1.8"
                            stroke-linecap="round" stroke-linejoin="round"
                            aria-hidden="true">
                            <rect x="3" y="5" width="13" height="14" rx="2"/>
                            <path d="m16 10 5-3v10l-5-3z"/>
                        </svg>
                    `,
                    className: "video"
                };

            case "Audio":
                return {
                    icon: `
                        <svg viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="1.8"
                            stroke-linecap="round" stroke-linejoin="round"
                            aria-hidden="true">
                            <path d="M12 3v18"/>
                            <path d="M8 7v10"/>
                            <path d="M4 10v4"/>
                            <path d="M16 6v12"/>
                            <path d="M20 9v6"/>
                        </svg>
                    `,
                    className: "audio"
                };

            case "URL":
                return {
                    icon: `
                        <svg viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="1.8"
                            stroke-linecap="round" stroke-linejoin="round"
                            aria-hidden="true">
                            <path d="M10 13a5 5 0 0 0 7.1 0l3-3a5 5 0 0 0-7.1-7.1l-1.7 1.7"/>
                            <path d="M14 11a5 5 0 0 0-7.1 0l-3 3a5 5 0 0 0 7.1 7.1l1.7-1.7"/>
                        </svg>
                    `,
                    className: "link"
                };

            default:
                return {
                    icon: `
                        <svg viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="1.8"
                            stroke-linecap="round" stroke-linejoin="round"
                            aria-hidden="true">
                            <path d="M6 3h9l5 5v13H6z"/>
                            <path d="M14 3v6h6"/>
                            <path d="M9 13h7"/>
                            <path d="M9 17h7"/>
                        </svg>
                    `,
                    className: "link"
                };
        }
    }

    // =========================================
    // 6. SELECT MEETING FILE
    // =========================================

    const allowedExtensions = [
        "mp4", "webm", "ogg", "mov", "avi",
        "mp3", "wav", "m4a",
        "pdf", "doc", "docx",
        "jpg", "jpeg", "png"
    ];

    if (filePicker && meetingFile) {
        filePicker.addEventListener("click", function () {
            meetingFile.click();
        });
    }

    if (meetingFile) {
        meetingFile.addEventListener("change", function () {
            const file = meetingFile.files[0];

            showMessage(fileInfo, "");
            showMessage(analysisMessage, "");

            if (!file) {
                if (selectedFilePreview) {
                    selectedFilePreview.hidden = true;
                }
                return;
            }

            const extension = getExtension(file.name);

            if (!allowedExtensions.includes(extension)) {
                showMessage(
                    fileInfo,
                    "Unsupported file type. Please choose a supported file.",
                    "error"
                );

                meetingFile.value = "";
                return;
            }

            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);

            const type = getMeetingType(file.name);
            const visual = getMeetingIcon(type);

            if (selectedFilePreview) {
                selectedFilePreview.hidden = false;

                selectedFileIcon.innerHTML = visual.icon;
                selectedFileIcon.className =
                    `selected-file-icon ${visual.className}`;

                selectedFileName.textContent = file.name;
                selectedFileMeta.textContent = `${type} · ${sizeMB} MB`;

                selectedFileType.textContent = type;
                selectedFileType.className =
                    `selected-file-type ${visual.className}`;
            }

            showMessage(fileInfo, "");

            if (meetingUrl) {
                meetingUrl.value = "";
            }

            showMessage(urlInfo, "");
        });
    }

    // =========================================
    // 7. VALIDATE MEETING URL
    // =========================================

    if (meetingUrl) {
        meetingUrl.addEventListener("input", function () {
            const url = meetingUrl.value.trim();

            showMessage(urlInfo, "");
            showMessage(analysisMessage, "");

            if (url && meetingFile) {
                meetingFile.value = "";
                showMessage(fileInfo, "");

                if (selectedFilePreview) {
                    selectedFilePreview.hidden = true;
                }
            }

            if (!url) return;

            if (isValidURL(url)) {
                showMessage(
                    urlInfo,
                    "Meeting URL format looks valid.",
                    "success"
                );
            } else {
                showMessage(
                    urlInfo,
                    "Enter a valid URL beginning with https:// or http://.",
                    "error"
                );
            }
        });
    }

    // =========================================
    // 8. ANALYZE MEETING
    // =========================================

    if (analyzeButton) {
        analyzeButton.addEventListener("click", async function () {
            const file = meetingFile?.files[0];
            const url = meetingUrl?.value.trim() || "";

            if (!file && !url) {
                showMessage(
                    analysisMessage,
                    "Please choose a meeting file or enter a meeting URL.",
                    "error"
                );
                return;
            }

            if (file && url) {
                showMessage(
                    analysisMessage,
                    "Please choose either a file or a URL, not both.",
                    "error"
                );
                return;
            }

            if (url && !isValidURL(url)) {
                showMessage(
                    analysisMessage,
                    "Please enter a valid HTTP or HTTPS URL.",
                    "error"
                );
                return;
            }

            const ext = file
                ? (file.name.split(".").pop() || "").toLowerCase()
                : "";

            const videoAudio = [
                "mp4", "webm", "mov", "mkv", "avi", "m4v",
                "mp3", "wav", "m4a", "ogg", "flac", "aac"
            ];

            const documents = ["pdf", "docx"];

            if (file && !videoAudio.includes(ext) && !documents.includes(ext)) {
                showMessage(
                    analysisMessage,
                    "The backend currently supports audio/video files and PDF/DOCX documents. Please choose a supported file.",
                    "error"
                );
                return;
            }

            analyzeButton.disabled = true;

            const originalText = analyzeButton.innerHTML;
            analyzeButton.textContent = "Analyzing meeting…";

            showMessage(
                analysisMessage,
                "Uploading and analyzing your meeting. This may take a few minutes."
            );

            try {
                let result;

                if (file) {
                    const form = new FormData();
                    form.append("file", file);

                    const endpoint = documents.includes(ext)
                        ? "/api/meetings/documents"
                        : "/api/meetings/transcribe";

                    const response = await fetch(endpoint, {
                        method: "POST",
                        body: form,
                        credentials: "same-origin"
                    });

                    result = await response.json().catch(() => ({}));

                    if (!response.ok) {
                        throw new Error(
                            result.detail || "Meeting processing failed."
                        );
                    }
                } else {
                    let host = "";

                    try {
                        host = new URL(url).hostname.toLowerCase();
                    } catch (_) {}

                    const youtube = [
                        "youtube.com",
                        "www.youtube.com",
                        "m.youtube.com",
                        "youtu.be",
                        "www.youtube-nocookie.com"
                    ].includes(host);

                    const response = await fetch(
                        "/api/meetings/transcribe-link",
                        {
                            method: "POST",
                            credentials: "same-origin",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                url,
                                input_type: youtube ? "youtube" : "meeting"
                            })
                        }
                    );

                    result = await response.json().catch(() => ({}));

                    if (!response.ok) {
                        throw new Error(
                            result.detail ||
                            "Could not analyze this URL. Some meeting platforms require a recording link or uploaded file."
                        );
                    }
                }

                const id = result.meeting_id || result.id;

                if (!id) {
                    throw new Error("The server did not return a meeting ID.");
                }

                const meeting = {
                    id: String(id),
                    name: result.filename || file?.name || url,
                    originalName: result.filename || file?.name || url,
                    type: file
                        ? (documents.includes(ext)
                            ? "Document"
                            : getMeetingType(file.name))
                        : "URL",
                    source: file ? "backend" : "url",
                    url: file ? "" : url,
                    date: new Date().toISOString(),
                    status: result.status || "Completed",
                    transcript: result.transcript || "",
                    summary: result.summary || ""
                };

                const meetings = MeetMind.readMeetings().filter(
                    item => String(item.id) !== String(id)
                );

                meetings.unshift(meeting);
                MeetMind.writeMeetings(meetings);

                window.location.href =
                    "/static/analysis.html?id=" + encodeURIComponent(id);

            } catch (error) {
                console.error("Meeting analysis failed:", error);

                showMessage(
                    analysisMessage,
                    error.message ||
                    "Could not analyze the meeting. Please try again.",
                    "error"
                );

                analyzeButton.disabled = false;
                analyzeButton.innerHTML = originalText;
            }
        });
    }

    // =========================================
    // 9. DISPLAY RECENT MEETINGS
    // =========================================

    async function renderRecentMeetings() {
        if (!meetingList) return;

        const query = (dashboardSearch?.value || "")
            .trim()
            .toLowerCase();

        try {
            const response = await fetch("/api/meetings", {
                method: "GET",
                credentials: "same-origin"
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(
                    data.detail || "Could not load your meetings."
                );
            }

            const allMeetings = Array.isArray(data.meetings)
                ? data.meetings
                : [];

            const meetings = allMeetings
                .filter(meeting =>
                    String(meeting.filename || "")
                        .toLowerCase()
                        .includes(query)
                )
                .slice(0, 3);

            meetingList.innerHTML = meetings.map(meeting => {
                const filename = meeting.filename || "Untitled Meeting";

                const extension = filename.split(".").pop().toLowerCase();

                const type = ["mp4", "webm", "mov", "avi", "ogg"].includes(extension)
                    ? "Video"
                    : ["mp3", "wav", "m4a"].includes(extension)
                        ? "Audio"
                        : ["pdf", "docx"].includes(extension)
                            ? "Document"
                            : "File";

                const visual = getMeetingIcon(type);

                const safeName = MeetMind.escapeHTML(filename);
                const safeType = MeetMind.escapeHTML(type);

                const safeId = encodeURIComponent(
                    String(meeting.meeting_id)
                );

                const parsedDate = new Date(meeting.created_at);

                const date = Number.isNaN(parsedDate.getTime())
                    ? "Date unavailable"
                    : parsedDate.toLocaleDateString("en-GB");

                return `
                    <article class="meeting-card">
                        <div class="meeting-type ${visual.className}-type">
                            ${visual.icon}
                        </div>

                        <div class="meeting-details">
                            <h3>${safeName}</h3>
                            <p>${date} · ${safeType}</p>

                            <span class="meeting-tag ${visual.className}-tag">
                                ${safeType}
                            </span>
                        </div>

                        <a
                            class="meeting-open"
                            href="/static/analysis.html?id=${safeId}"
                            aria-label="Open ${safeName}"
                        >
                            Open →
                        </a>
                    </article>
                `;
            }).join("");

            if (emptyRecent) {
                emptyRecent.hidden = meetings.length > 0;

                emptyRecent.textContent = query
                    ? "No meetings match your search."
                    : "Your saved meetings will appear here.";
            }

        } catch (error) {
            console.error("Could not load recent meetings:", error);

            meetingList.innerHTML = "";

            if (emptyRecent) {
                emptyRecent.hidden = false;
                emptyRecent.textContent = error.message;
            }
        }
    }

    // =========================================
    // 10. SEARCH RECENT MEETINGS
    // =========================================

    if (dashboardSearch) {
        dashboardSearch.addEventListener("input", function () {
            renderRecentMeetings();
        });
    }

    // =========================================
    // LOGOUT
    // =========================================

    // const logoutLink = document.getElementById("logoutLink");

    // if (logoutLink) {
    //     logoutLink.addEventListener("click", async function (event) {
    //         event.preventDefault();

    //         try {
    //             const response = await fetch("/api/auth/logout", {
    //                 method: "POST",
    //                 credentials: "same-origin"
    //             });

    //             if (!response.ok) {
    //                 throw new Error("Logout failed. Please try again.");
    //             }

    //             window.location.href = "/";

    //         } catch (error) {
    //             alert(error.message || "Unable to logout. Please try again.");
    //         }
    //     });
    // }

    // =========================================
    // 11. NOTIFICATION AND PROFILE BUTTONS
    // =========================================

    if (notificationButton) {
        notificationButton.addEventListener("click", function () {
            alert("You have no new notifications.");
        });
    }

    if (profileButton) {
        profileButton.addEventListener("click", function () {
            alert("You are viewing your MEETMIND AI workspace.");
        });
    }

    // =========================================
    // 12. INITIALIZE DASHBOARD
    // =========================================

    renderRecentMeetings();
});
