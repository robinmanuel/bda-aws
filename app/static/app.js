// Image Upload Preview Handler
function previewImage(input) {
  const file = input.files[0];
  const dropPlaceholder = document.getElementById("dropPlaceholder");
  const previewWrap = document.getElementById("previewWrap");
  const imagePreview = document.getElementById("imagePreview");

  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      imagePreview.src = e.target.result;
      previewWrap.style.display = "inline-block";
      dropPlaceholder.style.display = "none";
    };
    reader.readAsDataURL(file);
  }
}

function clearImageUpload() {
  const input = document.getElementById("image");
  const dropPlaceholder = document.getElementById("dropPlaceholder");
  const previewWrap = document.getElementById("previewWrap");
  const imagePreview = document.getElementById("imagePreview");

  input.value = "";
  imagePreview.src = "";
  previewWrap.style.display = "none";
  dropPlaceholder.style.display = "block";
}

// Architecture Modal Handlers
function openArchModal() {
  document.getElementById("archModal").style.display = "flex";
}

function closeArchModal() {
  document.getElementById("archModal").style.display = "none";
}

window.addEventListener("click", function(event) {
  const modal = document.getElementById("archModal");
  if (event.target === modal) {
    modal.style.display = "none";
  }
});

// Live AWS Infrastructure Status Checker
async function fetchLiveStatus() {
  const spinner = document.getElementById("statusSpinner");
  const btn = document.getElementById("refreshStatusBtn");
  
  if (spinner) spinner.classList.add("active");
  if (btn) btn.disabled = true;

  try {
    const resp = await fetch("/api/status");
    if (!resp.ok) throw new Error("Status check failed");
    const data = await resp.json();

    // Update EC2 Info
    if (data.ec2) {
      document.getElementById("statEc2Id").textContent = data.ec2.instance_id || "N/A";
      document.getElementById("statEc2Az").textContent = data.ec2.availability_zone || "N/A";
      document.getElementById("statEc2Ip").textContent = data.ec2.local_ipv4 || "N/A";

      const ec2Pill = document.getElementById("ec2StatusPill");
      if (data.ec2.is_ec2) {
        ec2Pill.textContent = "EC2 LIVE";
        ec2Pill.className = "status-pill status-ok";
      } else {
        ec2Pill.textContent = "DEV HOST";
        ec2Pill.className = "status-pill status-warn";
      }
    }

    // Update RDS Info
    if (data.rds) {
      const rdsPill = document.getElementById("rdsStatusPill");
      const rdsLatency = document.getElementById("statRdsLatency");
      
      if (data.rds.connected) {
        rdsPill.textContent = "CONNECTED";
        rdsPill.className = "status-pill status-ok";
        rdsLatency.textContent = `${data.rds.latency_ms} ms`;
      } else {
        rdsPill.textContent = "DISCONNECTED";
        rdsPill.className = "status-pill status-warn";
        rdsLatency.textContent = "ERR";
      }
    }

    // Update S3 Info
    if (data.s3) {
      const s3Pill = document.getElementById("s3StatusPill");
      const s3Bucket = document.getElementById("statS3Bucket");
      const s3Auth = document.getElementById("statS3Auth");

      if (data.s3.bucket) {
        s3Bucket.textContent = data.s3.bucket;
      }
      if (data.s3.auth) {
        s3Auth.textContent = data.s3.auth;
      }

      if (data.s3.connected) {
        s3Pill.textContent = data.s3.bucket ? "S3 ONLINE" : "LOCAL READY";
        s3Pill.className = "status-pill status-ok";
      } else {
        s3Pill.textContent = "ERROR";
        s3Pill.className = "status-pill status-warn";
      }
    }

  } catch (err) {
    console.error("Failed to query live status:", err);
  } finally {
    if (spinner) spinner.classList.remove("active");
    if (btn) btn.disabled = false;
  }
}

// Initial status fetch on page load
document.addEventListener("DOMContentLoaded", () => {
  fetchLiveStatus();
});
