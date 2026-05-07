document.addEventListener('DOMContentLoaded', () => {
    // ---- Navigation Elements ----
    const menuBtn = document.getElementById('menu-btn');
    const navDrawer = document.getElementById('nav-drawer');
    const drawerOverlay = document.getElementById('drawer-overlay');
    const navLinks = document.querySelectorAll('.nav-link');
    const views = document.querySelectorAll('.view');
    const pageTitle = document.getElementById('page-title');

    function toggleDrawer() {
        navDrawer.classList.toggle('open');
        drawerOverlay.classList.toggle('open');
    }

    menuBtn.addEventListener('click', toggleDrawer);
    drawerOverlay.addEventListener('click', toggleDrawer);

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navLinks.forEach(l => l.classList.remove('active'));
            views.forEach(v => v.classList.remove('active'));
            link.classList.add('active');

            const targetId = link.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');

            if (targetId === 'view-live') {
                pageTitle.textContent = 'Live Video';
                fetchUsers();
                if (typeof toggleCameraState === 'function') toggleCameraState(true);
            } else if (targetId === 'view-register') {
                pageTitle.textContent = 'Face Registration';
                if (typeof toggleCameraState === 'function') toggleCameraState(false);
            }

            if (window.innerWidth <= 768) {
                toggleDrawer();
            }
        });
    });

    // ---- Material Ripple Effect ----
    document.addEventListener('mousedown', function (e) {
        if (e.target.matches('.register-btn, .action-btn, .reg-card') || e.target.closest('.reg-card')) {
            const target = e.target.matches('.reg-card') ? e.target : (e.target.closest('.reg-card') || e.target);
            const rect = target.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const ripple = document.createElement('span');
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            ripple.style.position = 'absolute';
            ripple.style.background = 'rgba(26, 115, 232, 0.15)';
            if (target.classList.contains('register-btn')) {
                ripple.style.background = 'rgba(255, 255, 255, 0.3)';
            }
            ripple.style.transform = 'translate(-50%, -50%)';
            ripple.style.borderRadius = '50%';
            ripple.style.animation = 'ripple 0.6s linear';
            ripple.style.pointerEvents = 'none';

            const currentPosition = window.getComputedStyle(target).position;
            if (currentPosition === 'static') {
                target.style.position = 'relative';
            }
            target.style.overflow = 'hidden';
            target.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        }
    });

    // ---- API LOGIC ----
    const regListContainer = document.getElementById('registration-list');
    const recentLogsContainer = document.getElementById('recent-logs');

    // Form Inputs
    const registerBtn = document.querySelector('.register-btn');
    const idInput = document.getElementById('reg-id');
    const nameInput = document.getElementById('reg-name');
    const genderSelect = document.getElementById('reg-gender');
    const facultyInput = document.getElementById('reg-faculty');
    const deptInput = document.getElementById('reg-dept');

    async function fetchUsers() {
        try {
            const res = await fetch('/api/users');
            if (!res.ok) throw new Error("Failed to fetch users");
            const users = await res.json();

            window.allUsers = users;
            const badge = document.getElementById('total-users-badge');
            if (badge) badge.textContent = `Total: ${users.length}`;

            renderUsers(users);
        } catch (err) {
            console.error(err);
            regListContainer.innerHTML = `<div style="text-align: center; color: red; padding: 20px;">Failed to load users. Is backend running?</div>`;
        }
    }

    function renderUsers(usersToRender) {
        regListContainer.innerHTML = '';
        if (usersToRender.length === 0) {
            regListContainer.innerHTML = `<div style="text-align: center; color: var(--text-secondary); padding: 20px;">No users found.</div>`;
        } else {
            usersToRender.forEach(u => {
                const card = document.createElement('div');
                card.className = 'reg-card';
                card.innerHTML = `
                    <div class="reg-avatar"><span class="material-symbols-outlined">person</span></div>
                    <div class="reg-info">
                        <span class="reg-id" style="color: var(--text-primary); font-size: 14px; font-weight: 600;">${u.name}</span>
                        <span class="reg-name" style="color: var(--text-secondary); font-size: 11px; font-weight: 500;">ID: ${u.id}</span>
                    </div>
                    <div class="reg-actions">
                        <span class="material-symbols-outlined edit-btn" title="Edit">edit</span>
                        <span class="material-symbols-outlined delete-btn" title="Delete">delete</span>
                    </div>
                `;

                card.querySelector('.edit-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    alert("Edit functionality to be implemented.");
                });

                card.querySelector('.delete-btn').addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (confirm(`Are you sure you want to delete ${u.name}?`)) {
                        try {
                            const delRes = await fetch(`/api/users/${u.id}`, { method: 'DELETE' });
                            if (delRes.ok) {
                                fetchUsers();
                            } else {
                                alert("Failed to delete user.");
                            }
                        } catch (err) {
                            alert("Error connecting to server.");
                        }
                    }
                });

                regListContainer.appendChild(card);
            });
        }
    }

    const searchInput = document.getElementById('search-users');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            if (window.allUsers) {
                const filtered = window.allUsers.filter(u =>
                    u.id.toLowerCase().includes(query) ||
                    u.name.toLowerCase().includes(query)
                );
                renderUsers(filtered);
            }
        });
    }

    const addUserBtn = document.getElementById('add-new-user-btn');
    if (addUserBtn) {
        addUserBtn.addEventListener('click', () => {
            idInput.focus();
        });
    }

    async function fetchLogs() {
        try {
            const res = await fetch('/api/logs');
            if (!res.ok) return;
            const logs = await res.json();

            if (logs.length > 0) {
                recentLogsContainer.innerHTML = '';
                logs.forEach(log => {
                    const div = document.createElement('div');
                    div.className = 'reg-card';
                    div.style.backgroundColor = '#e8f0fe';
                    
                    let avatarHtml = `<span class="material-symbols-outlined">person_check</span>`;
                    if (log.image) {
                        avatarHtml = `<img src="data:image/jpeg;base64,${log.image}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
                    }
                    
                    div.innerHTML = `
                        <div class="reg-avatar" style="background-color: var(--primary-color); color: white; padding: 0; overflow: hidden;">
                            ${avatarHtml}
                        </div>
                        <div class="reg-info">
                            <span class="reg-id" style="color: var(--primary-color);">${log.name}</span>
                            <span class="reg-name">${log.time}</span>
                        </div>
                    `;
                    recentLogsContainer.appendChild(div);
                });
            }
        } catch (err) {
            // Silently fail if backend isn't ready
        }
    }

    // Handle File Upload Previews
    [1, 2, 3].forEach(id => {
        const fileInput = document.getElementById(`file-${id}`);
        const imgEl = document.getElementById(`img-${id}`);
        const iconEl = document.getElementById(`icon-${id}`);

        fileInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (event) {
                    imgEl.src = event.target.result;
                    imgEl.style.display = 'block';
                    iconEl.style.display = 'none';
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // Helper: Convert data URI to Blob for upload
    function dataURItoBlob(dataURI) {
        const byteString = atob(dataURI.split(',')[1]);
        const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
        const ab = new ArrayBuffer(byteString.length);
        const ia = new Uint8Array(ab);
        for (let i = 0; i < byteString.length; i++) {
            ia[i] = byteString.charCodeAt(i);
        }
        return new Blob([ab], { type: mimeString });
    }

    registerBtn.addEventListener('click', async () => {
        const id = idInput.value.trim();
        const name = nameInput.value.trim();
        const gender = genderSelect.value;
        const faculty = facultyInput.value.trim();
        const dept = deptInput.value.trim();

        if (!id || !name || !gender || !faculty || !dept) {
            alert("Please fill all form fields.");
            return;
        }

        const img1 = document.getElementById('img-1');
        if (img1.style.display === 'none' || !img1.src) {
            alert("Please upload an image in the first slot!");
            return;
        }

        registerBtn.disabled = true;
        registerBtn.textContent = "Processing Features...";

        try {
            const formData = new FormData();
            formData.append("id", id);
            formData.append("name", name);
            formData.append("gender", gender);
            formData.append("faculty", faculty);
            formData.append("department", dept);

            // Append the front image blob
            formData.append("image", dataURItoBlob(img1.src), "front.jpg");

            // Append left image if available
            const img2 = document.getElementById('img-2');
            if (img2 && img2.style.display !== 'none' && img2.src) {
                formData.append("image_left", dataURItoBlob(img2.src), "left.jpg");
            }

            // Append right image if available
            const img3 = document.getElementById('img-3');
            if (img3 && img3.style.display !== 'none' && img3.src) {
                formData.append("image_right", dataURItoBlob(img3.src), "right.jpg");
            }

            const response = await fetch('/api/register', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                alert("Registration Successful!");
                idInput.value = "";
                nameInput.value = "";
                genderSelect.value = "";
                facultyInput.value = "";
                deptInput.value = "";

                img1.style.display = 'none';
                document.getElementById('icon-1').style.display = 'block';
                img1.src = "";

                fetchUsers();
                document.querySelector('[data-target="view-live"]').click();
            } else {
                alert("Error: " + data.detail);
            }
        } catch (err) {
            console.error(err);
            alert("Failed to connect to backend server.");
        }

        registerBtn.disabled = false;
        registerBtn.textContent = "Register";
    });

    // Start fetching users and polling logs
    fetchUsers();
    setInterval(fetchLogs, 1000); // Poll logs every 1 second

    // ---- Camera Toggle Logic ----
    const toggleCamBtn = document.getElementById('toggle-cam-btn');
    const toggleCamIcon = document.getElementById('toggle-cam-icon');
    const liveVideo = document.getElementById('live-video');
    const videoPlaceholder = document.getElementById('video-placeholder');
    window.isCameraActive = true; // Use window to allow access from nav logic

    window.toggleCameraState = async function(state) {
        if (window.isCameraActive === state) return;
        window.isCameraActive = state;

        if (window.isCameraActive) {
            if(toggleCamIcon) {
                toggleCamIcon.textContent = 'videocam';
                toggleCamIcon.style.color = 'var(--text-secondary)';
            }
            if(liveVideo) {
                liveVideo.src = '/video_feed?' + new Date().getTime();
                liveVideo.style.display = 'block';
            }
            if(videoPlaceholder) videoPlaceholder.style.display = 'none';
        } else {
            if(toggleCamIcon) {
                toggleCamIcon.textContent = 'videocam_off';
                toggleCamIcon.style.color = '#d93025';
            }
            if(liveVideo) liveVideo.style.display = 'none';
            if(videoPlaceholder) videoPlaceholder.style.display = 'flex';
            const statusEl = document.getElementById('camera-status');
            if(statusEl) statusEl.textContent = 'Camera Off';
        }

        try {
            const formData = new FormData();
            formData.append('state', window.isCameraActive);
            await fetch('/api/camera/toggle', { method: 'POST', body: formData });
        } catch(err) {
            console.error(err);
        }
    }

    async function checkCameraStatus() {
        try {
            const res = await fetch('/api/camera/status');
            const data = await res.json();
            // Force state to update UI
            window.isCameraActive = !data.camera_active;
            window.toggleCameraState(data.camera_active);
        } catch (err) {}
    }

    if (toggleCamBtn) {
        toggleCamBtn.addEventListener('click', () => {
            window.toggleCameraState(!window.isCameraActive);
        });
        checkCameraStatus();
    }

    // ---- Webcam Capture Logic ----
    const webcamModal = document.getElementById('webcam-modal');
    const webcamVideo = document.getElementById('webcam-video');
    const webcamCanvas = document.getElementById('webcam-canvas');
    const closeWebcamBtn = document.getElementById('close-webcam-btn');
    let currentCaptureTarget = null;
    let localStream = null;

    document.querySelectorAll('.webcam-capture-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            currentCaptureTarget = e.target.getAttribute('data-target');
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: true });
                webcamVideo.srcObject = localStream;
                webcamModal.style.display = 'flex';
            } catch (err) {
                console.error("Camera access denied or unavailable", err);
                alert("Could not access camera. Make sure it's not being used by another application.");
            }
        });
    });

    function closeWebcam() {
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
        }
        webcamVideo.srcObject = null;
        webcamModal.style.display = 'none';
        currentCaptureTarget = null;
    }

    if(closeWebcamBtn) closeWebcamBtn.addEventListener('click', closeWebcam);

    // Spacebar capture
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && webcamModal && webcamModal.style.display === 'flex' && currentCaptureTarget) {
            e.preventDefault(); // Prevent page scroll down
            
            // Draw video frame to canvas
            webcamCanvas.width = webcamVideo.videoWidth;
            webcamCanvas.height = webcamVideo.videoHeight;
            const ctx = webcamCanvas.getContext('2d');
            
            // We flip the image horizontally since the video is mirrored via CSS
            ctx.translate(webcamCanvas.width, 0);
            ctx.scale(-1, 1);
            ctx.drawImage(webcamVideo, 0, 0, webcamCanvas.width, webcamCanvas.height);
            
            // Convert to data URL
            const dataUrl = webcamCanvas.toDataURL('image/jpeg');
            
            // Set image to the target slot
            const imgEl = document.getElementById(`img-${currentCaptureTarget}`);
            const iconEl = document.getElementById(`icon-${currentCaptureTarget}`);
            if(imgEl && iconEl) {
                imgEl.src = dataUrl;
                imgEl.style.display = 'block';
                iconEl.style.display = 'none';
            }
            
            closeWebcam();
        }
    });
});
