// =============================================================================
// Personal Diary — Chill UI & Abstracted AWS Telemetry Controller
// =============================================================================

// 1. Polaroid Memory Photo Preview
function previewMemory(input) {
  const file = input.files[0];
  const placeholder = document.getElementById("photoPlaceholder");
  const preview = document.getElementById("polaroidPreview");
  const img = document.getElementById("imagePreview");

  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      img.src = e.target.result;
      preview.style.display = "inline-block";
      placeholder.style.display = "none";
    };
    reader.readAsDataURL(file);
  }
}

function removeMemoryPhoto() {
  const input = document.getElementById("image");
  const placeholder = document.getElementById("photoPlaceholder");
  const preview = document.getElementById("polaroidPreview");
  const img = document.getElementById("imagePreview");

  input.value = "";
  img.src = "";
  preview.style.display = "none";
  placeholder.style.display = "flex";
}

// 2. Slide-Over Architecture Drawer Handlers
function openArchDrawer() {
  const drawer = document.getElementById("archDrawer");
  const overlay = document.getElementById("archDrawerOverlay");
  if (drawer && overlay) {
    drawer.classList.add("open");
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }
}

function closeArchDrawer() {
  const drawer = document.getElementById("archDrawer");
  const overlay = document.getElementById("archDrawerOverlay");
  if (drawer && overlay) {
    drawer.classList.remove("open");
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }
}

// Close drawer on Escape key
document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    closeArchDrawer();
  }
});

// 3. Live AWS Infrastructure Telemetry Fetcher
async function refreshSpecs() {
  const spinner = document.getElementById("specsSpinner");
  const btn = document.getElementById("drawerRefreshBtn");

  if (spinner) spinner.classList.add("active");
  if (btn) btn.disabled = true;

  try {
    const resp = await fetch("/api/status");
    if (!resp.ok) throw new Error("Status API returned error");
    const data = await resp.json();

    // Update Header Cloud Sync Chip
    const syncLabel = document.getElementById("cloudSyncLabel");
    if (syncLabel) {
      if (data.ec2 && data.ec2.is_ec2) {
        syncLabel.textContent = "AWS Cloud Synced";
      } else {
        syncLabel.textContent = "Cloud Synced";
      }
    }

    // Update Compute Spec (EC2)
    if (data.ec2) {
      const ec2Id = document.getElementById("drawerEc2Id");
      const ec2Az = document.getElementById("drawerEc2Az");
      const ec2Ip = document.getElementById("drawerEc2Ip");
      const ec2Status = document.getElementById("drawerEc2Status");

      if (ec2Id) ec2Id.textContent = data.ec2.instance_id || "N/A";
      if (ec2Az) ec2Az.textContent = data.ec2.availability_zone || "N/A";
      if (ec2Ip) ec2Ip.textContent = data.ec2.local_ipv4 || "127.0.0.1";
      if (ec2Status) {
        ec2Status.textContent = data.ec2.is_ec2 ? "EC2 LIVE" : "DEV HOST";
      }
    }

    // Update Database Spec (RDS)
    if (data.rds) {
      const rdsHost = document.getElementById("drawerRdsHost");
      const rdsLatency = document.getElementById("drawerRdsLatency");
      const rdsStatus = document.getElementById("drawerRdsStatus");

      if (rdsHost && data.rds.engine) {
        rdsHost.textContent = data.rds.engine.length > 22 ? data.rds.engine.substring(0, 22) + "..." : data.rds.engine;
      }
      if (rdsLatency) {
        rdsLatency.textContent = `${data.rds.latency_ms} ms`;
      }
      if (rdsStatus) {
        rdsStatus.textContent = data.rds.connected ? "CONNECTED" : "DISCONNECTED";
      }
    }

    // Update Storage Spec (S3)
    if (data.s3) {
      const s3Bucket = document.getElementById("drawerS3Bucket");
      const s3Auth = document.getElementById("drawerS3Auth");
      const s3Status = document.getElementById("drawerS3Status");

      if (s3Bucket && data.s3.bucket) {
        s3Bucket.textContent = data.s3.bucket;
      }
      if (s3Auth && data.s3.auth) {
        s3Auth.textContent = data.s3.auth;
      }
      if (s3Status) {
        s3Status.textContent = data.s3.bucket ? "S3 ONLINE" : "READY (LOCAL)";
      }
    }

  } catch (err) {
    console.error("Telemetry fetch error:", err);
  } finally {
    if (spinner) spinner.classList.remove("active");
    if (btn) btn.disabled = false;
  }
}

// Initial fetch on page load
document.addEventListener("DOMContentLoaded", () => {
  refreshSpecs();
});
