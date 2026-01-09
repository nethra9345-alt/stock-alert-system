function checkStock() {

    const available = parseInt(document.getElementById("available").value);
    const minimum = parseInt(document.getElementById("minimum").value);
    const result = document.getElementById("result");

    if (isNaN(available) || isNaN(minimum)) {
        result.innerText = "Please enter valid values";
        result.className = "";
        return;
    }

    // Threshold Logic
    if (available <= minimum * 0.3) {
        result.innerText = "CRITICAL STOCK 🚨";
        result.className = "critical";
    }
    else if (available < minimum) {
        result.innerText = "LOW STOCK ⚠️";
        result.className = "low";
    }
    else {
        result.innerText = "STOCK OK ✅";
        result.className = "ok";
    }
}
