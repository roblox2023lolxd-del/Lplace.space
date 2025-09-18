document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginFormEl");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const mode = document.querySelector("input[name='mode']:checked").value;

    const endpoint = mode === "login" ? "/login" : "/signup";

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();

      if (data.success) {
        window.location.href = "index.html";
      } else {
        alert(data.message || "Login/Sign-up failed");
      }
    } catch (err) {
      console.error(err);
      alert("Error connecting to server");
    }
  });
});
