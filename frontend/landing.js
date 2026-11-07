
"use strict";

document.addEventListener("DOMContentLoaded", function () {
  const root = document.documentElement;
  const themeToggle = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");
  const menuToggle = document.getElementById("menuToggle");
  const navLinks = document.getElementById("navLinks");
  const demoContent = document.getElementById("demoContent");
  const demoTabs = document.querySelectorAll(".demo-tab");

  const THEME_KEY = "meetMindTheme";

  // SVG icons for the theme toggle.
  // Moon is shown in light mode; sun is shown in dark mode.
  const moonIcon = `
    <svg viewBox="0 0 24 24"
         fill="none"
         stroke="currentColor"
         stroke-width="1.8"
         stroke-linecap="round"
         stroke-linejoin="round"
         aria-hidden="true">
      <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5
               8.5 8.5 0 1 0 20.5 14.2z"/>
    </svg>
  `;

  const sunIcon = `
    <svg viewBox="0 0 24 24"
         fill="none"
         stroke="currentColor"
         stroke-width="1.8"
         stroke-linecap="round"
         stroke-linejoin="round"
         aria-hidden="true">
      <circle cx="12" cy="12" r="4"/>
      <path d="M12 2v2"/>
      <path d="M12 20v2"/>
      <path d="m4.93 4.93 1.42 1.42"/>
      <path d="m17.65 17.65 1.42 1.42"/>
      <path d="M2 12h2"/>
      <path d="M20 12h2"/>
      <path d="m4.93 19.07 1.42-1.42"/>
      <path d="m17.65 6.35 1.42-1.42"/>
    </svg>
  `;

  // Read the previously selected theme.
  function readSavedTheme() {
    try {
      const savedTheme = localStorage.getItem(THEME_KEY);

      if (savedTheme === "dark" || savedTheme === "light") {
        return savedTheme;
      }
    } catch (error) {
      console.warn("Unable to read the saved theme.", error);
    }

    return "light";
  }

  // Apply the theme and update the icon.
  function applyTheme(theme, savePreference = true) {
    const isDark = theme === "dark";

    // Update the theme used by the landing page CSS.
    root.setAttribute("data-theme", isDark ? "dark" : "light");

    // Update the icon without replacing it with a text symbol.
    if (themeIcon) {
      themeIcon.innerHTML = isDark ? sunIcon : moonIcon;
    }

    // Update accessibility information.
    if (themeToggle) {
      const label = isDark
        ? "Switch to light mode"
        : "Switch to dark mode";

      themeToggle.setAttribute("aria-label", label);
      themeToggle.setAttribute("title", label);
      themeToggle.setAttribute("aria-pressed", String(isDark));
    }

    // Remember the user's preference.
    if (savePreference) {
      try {
        localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
      } catch (error) {
        console.warn("Unable to save the theme preference.", error);
      }
    }
  }

  // Initialize the saved theme without rewriting the preference.
  applyTheme(readSavedTheme(), false);

  // Toggle between light and dark mode.
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      const currentTheme = root.getAttribute("data-theme") || "light";
      const nextTheme = currentTheme === "dark" ? "light" : "dark";

      applyTheme(nextTheme);
    });
  }

  // Mobile navigation.
  if (menuToggle && navLinks) {
    menuToggle.addEventListener("click", function () {
      const isOpen = navLinks.classList.toggle("open");

      menuToggle.setAttribute("aria-expanded", String(isOpen));
    });

    navLinks.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        navLinks.classList.remove("open");
        menuToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Interactive demo content.
  const examples = {
    summary: {
      label: "EXECUTIVE SUMMARY",
      title: "Product Planning Meeting",
      description:
        "The team reviewed product priorities, discussed the upcoming development timeline and identified improvements to the user experience.",
      heading: "Suggested next steps",
      items: [
        "Confirm the project requirements and priorities.",
        "Review the development timeline with the team.",
        "Prepare the next progress update."
      ]
    },

    decisions: {
      label: "KEY DECISIONS",
      title: "Meeting Decisions",
      description:
        "The team agreed to prioritize the core user experience, review project milestones and keep the next release focused on essential improvements.",
      heading: "Decisions to remember",
      items: [
        "Prioritize essential product improvements.",
        "Review milestones before the next release.",
        "Share agreed decisions with the project team."
      ]
    },

    actions: {
      label: "ACTION ITEMS",
      title: "Follow-up Tasks",
      description:
        "A useful meeting record makes responsibilities and follow-up work easier to review after the discussion.",
      heading: "Example task list",
      items: [
        "Confirm requirements with stakeholders.",
        "Prepare a development progress update.",
        "Schedule a follow-up review."
      ]
    },

    transcript: {
      label: "TRANSCRIPT EXAMPLE",
      title: "Conversation Excerpt",
      description:
        "Speaker 1: Let's review the priorities for the next release. Speaker 2: We should confirm the requirements first and then agree on the timeline.",
      heading: "Points to review",
      items: [
        "Review the upcoming release priorities.",
        "Confirm the requirements before development.",
        "Agree on a project timeline."
      ]
    },

    assistant: {
      label: "AI ASSISTANT EXAMPLE",
      title: "Ask About a Meeting",
      description:
        "Example question: What were the main priorities discussed? A configured AI assistant could use the available meeting information to formulate a relevant answer.",
      heading: "Example questions",
      items: [
        "What decisions were made?",
        "Which tasks need follow-up?",
        "What should the team review next?"
      ]
    }
  };

  function renderDemo(key) {
    if (!demoContent || !examples[key]) {
      return;
    }

    const item = examples[key];

    const label = document.createElement("span");
    label.className = "demo-content-kicker";
    label.textContent = item.label;

    const title = document.createElement("h3");
    title.textContent = item.title;

    const description = document.createElement("p");
    description.textContent = item.description;

    const divider = document.createElement("div");
    divider.className = "demo-divider";

    const heading = document.createElement("h4");
    heading.textContent = item.heading;

    const list = document.createElement("ul");
    list.className = "demo-list";

    item.items.forEach(function (text, index) {
      const li = document.createElement("li");
      const number = document.createElement("span");

      number.textContent = String(index + 1).padStart(2, "0");

      li.appendChild(number);
      li.appendChild(document.createTextNode(text));

      list.appendChild(li);
    });

    demoContent.replaceChildren(
      label,
      title,
      description,
      divider,
      heading,
      list
    );
  }

  // Switch between demo tabs.
  demoTabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      demoTabs.forEach(function (otherTab) {
        otherTab.classList.remove("active");
        otherTab.setAttribute("aria-selected", "false");
      });

      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");

      if (demoContent) {
        demoContent.setAttribute("aria-labelledby", tab.id);
      }

      renderDemo(tab.dataset.tab);
    });
  });

  // Display the current year in the footer.
  const year = document.getElementById("year");

  if (year) {
    year.textContent = new Date().getFullYear();
  }
});
