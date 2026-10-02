async function askEduGenie() {
    const prompt = document.getElementById("promptInput").value.trim();
    const resultBox = document.getElementById("askResult");

    if (!prompt) {
        alert("Please enter a concept or question!");
        return;
    }

    resultBox.style.display = "block";
    resultBox.innerHTML = "<em>EduGenie is analyzing your request...</em>";

    try {
        const response = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: prompt })
        });
        const data = await response.json();
        if (data.reply) {
            resultBox.innerHTML = marked.parse(data.reply);
        } else {
            resultBox.innerText = data.error || "An error occurred.";
        }
    } catch (err) {
        resultBox.innerText = "Error: " + err.message;
    }
}

async function generateQuiz() {
    const topic = document.getElementById("quizTopic").value.trim();
    const level = document.getElementById("bloomLevel").value;
    const resultBox = document.getElementById("quizResult");

    if (!topic) {
        alert("Please enter a quiz topic!");
        return;
    }

    resultBox.style.display = "block";
    resultBox.innerHTML = "<em>Crafting quiz with Bloom's Taxonomy...</em>";

    try {
        const response = await fetch("/quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic: topic, level: level })
        });
        const data = await response.json();
        if (data.quiz) {
            resultBox.innerHTML = marked.parse(data.quiz);
        } else {
            resultBox.innerText = data.error || "An error occurred.";
        }
    } catch (err) {
        resultBox.innerText = "Error: " + err.message;
    }
}