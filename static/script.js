document.addEventListener("DOMContentLoaded", function () {
    console.log("JavaScript Loaded!");

    // Smooth page transitions
    document.body.style.opacity = "0";
    setTimeout(() => {
        document.body.style.transition = "opacity 1s";
        document.body.style.opacity = "1";
    }, 100);

    // Dark mode toggle
    const toggleDarkMode = document.createElement("button");
    toggleDarkMode.innerText = "🌙 Dark Mode";
    toggleDarkMode.style.position = "fixed";
    toggleDarkMode.style.top = "10px";
    toggleDarkMode.style.right = "10px";
    toggleDarkMode.style.padding = "8px 12px";
    toggleDarkMode.style.cursor = "pointer";
    document.body.appendChild(toggleDarkMode);

    toggleDarkMode.addEventListener("click", function () {
        document.body.classList.toggle("dark-mode");
        if (document.body.classList.contains("dark-mode")) {
            toggleDarkMode.innerText = "☀️ Light Mode";
        } else {
            toggleDarkMode.innerText = "🌙 Dark Mode";
        }
    });

    // Dark mode styles
    const style = document.createElement("style");
    style.innerHTML = `
        .dark-mode {
            background-color: #121212;
            color: white;
        }
        .dark-mode table {
            background-color: #333;
            color: white;
        }
    `;
    document.head.appendChild(style);

    // Button animation
    document.querySelectorAll("button").forEach(button => {
        button.addEventListener("mouseenter", () => {
            button.style.transform = "scale(1.1)";
            button.style.transition = "transform 0.2s";
        });
        button.addEventListener("mouseleave", () => {
            button.style.transform = "scale(1)";
        });
    });

    // Table row highlight on hover
    document.querySelectorAll("table tr").forEach(row => {
        row.addEventListener("mouseenter", () => {
            row.style.backgroundColor = "#f1f1f1";
            row.style.transition = "background-color 0.3s";
        });
        row.addEventListener("mouseleave", () => {
            row.style.backgroundColor = "";
        });
    });

    // Form validation alert
    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", function (event) {
            let inputs = form.querySelectorAll("input");
            let isValid = true;
            inputs.forEach(input => {
                if (input.value.trim() === "") {
                    isValid = false;
                    input.style.border = "2px solid red";
                } else {
                    input.style.border = "1px solid #ccc";
                }
            });

            if (!isValid) {
                event.preventDefault();
                alert("Please fill in all fields!");
            }
        });
    });
});
