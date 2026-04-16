document.addEventListener("DOMContentLoaded", () => {
    const ratingInput = document.getElementById("rating-value");
    const ratingLabel = document.getElementById("rating-label");
    const ratingGroup = document.querySelector("[data-rating-group]");
    const starButtons = Array.from(document.querySelectorAll(".star-btn"));
    const labels = {
        1: "Poor",
        2: "Fair",
        3: "Good",
        4: "Very Good",
        5: "Excellent",
    };

    if (!ratingInput || !ratingLabel || !ratingGroup || starButtons.length === 0) {
        return;
    }

    let currentRating = 0;

    const updateStars = (value) => {
        starButtons.forEach((button) => {
            const buttonRating = Number(button.dataset.rating);
            button.classList.toggle("is-active", buttonRating <= value);
        });
    };

    starButtons.forEach((button) => {
        const value = Number(button.dataset.rating);

        button.addEventListener("click", () => {
            currentRating = value;
            ratingInput.value = String(value);
            ratingLabel.textContent = labels[value] || "";
            updateStars(value);
        });

        button.addEventListener("mouseenter", () => {
            updateStars(value);
        });
    });

    ratingGroup.addEventListener("mouseleave", () => {
        updateStars(currentRating);
    });
});
