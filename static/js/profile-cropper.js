(function () {
    "use strict";

    function initProfileCropper() {
        const input = document.getElementById("profile_photo");
        const chooseBtn = document.getElementById("chooseProfilePhotoBtn");
        const modal = document.getElementById("profileCropModal");
        const stage = document.getElementById("profileCropStage");
        const image = document.getElementById("profileCropImage");
        const zoomInput = document.getElementById("profileCropZoom");
        const resetBtn = document.getElementById("profileCropReset");
        const saveBtn = document.getElementById("profileCropSave");
        const status = document.getElementById("profilePhotoStatus");
        const preview = document.getElementById("profilePhotoPreview");

        if (!input || !chooseBtn || !modal || !stage || !image || !zoomInput || !resetBtn || !saveBtn) {
            return;
        }

        const closeButtons = modal.querySelectorAll("[data-crop-close]");
        const uploadUrl = input.dataset.uploadUrl || "/admin/profile-photo";

        let objectUrl = null;
        let minScale = 1;
        let scale = 1;
        let offsetX = 0;
        let offsetY = 0;
        let dragging = false;
        let lastX = 0;
        let lastY = 0;

        function setStatus(message, type) {
            if (!status) return;
            status.textContent = message || "";
            status.classList.remove("is-error", "is-success");
            if (type === "error") status.classList.add("is-error");
            if (type === "success") status.classList.add("is-success");
        }

        function stageSize() {
            return Math.max(1, stage.getBoundingClientRect().width);
        }

        function clampOffsets() {
            if (!image.naturalWidth || !image.naturalHeight) return;

            const size = stageSize();
            const scaledWidth = image.naturalWidth * scale;
            const scaledHeight = image.naturalHeight * scale;
            const limitX = Math.max(0, (scaledWidth - size) / 2);
            const limitY = Math.max(0, (scaledHeight - size) / 2);

            offsetX = Math.min(limitX, Math.max(-limitX, offsetX));
            offsetY = Math.min(limitY, Math.max(-limitY, offsetY));
        }

        function renderCrop() {
            clampOffsets();
            image.style.transform =
                "translate(-50%, -50%) translate(" +
                offsetX +
                "px, " +
                offsetY +
                "px) scale(" +
                scale +
                ")";
        }

        function resetCrop() {
            if (!image.naturalWidth || !image.naturalHeight) return;

            const size = stageSize();
            minScale = Math.max(
                size / image.naturalWidth,
                size / image.naturalHeight
            );

            scale = minScale;
            offsetX = 0;
            offsetY = 0;
            zoomInput.value = "1";
            renderCrop();
        }

        function showModal() {
            modal.classList.add("open");
            modal.setAttribute("aria-hidden", "false");
            document.body.style.overflow = "hidden";
        }

        function closeModal(clearFile) {
            modal.classList.remove("open");
            modal.setAttribute("aria-hidden", "true");
            document.body.style.overflow = "";
            dragging = false;
            stage.classList.remove("is-dragging");

            if (clearFile) input.value = "";

            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }

            image.removeAttribute("src");
        }

        function openCropper(file) {
            setStatus("", "");
            showModal();

            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
            }

            objectUrl = URL.createObjectURL(file);

            image.onload = function () {
                requestAnimationFrame(function () {
                    resetCrop();
                });
            };

            image.onerror = function () {
                closeModal(true);
                setStatus("This image could not be opened. Try a JPG, PNG, or WEBP file.", "error");
            };

            image.src = objectUrl;
        }

        chooseBtn.addEventListener("click", function () {
            input.value = "";
            input.click();
        });

        input.addEventListener("change", function () {
            const file = input.files && input.files[0];
            if (!file) return;

            const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
            if (file.type && !allowedTypes.includes(file.type)) {
                input.value = "";
                setStatus("Please choose a JPG, PNG, or WEBP image.", "error");
                return;
            }

            openCropper(file);
        });

        zoomInput.addEventListener("input", function () {
            const previousScale = scale;
            scale = minScale * Number(zoomInput.value || 1);

            if (previousScale > 0) {
                const ratio = scale / previousScale;
                offsetX *= ratio;
                offsetY *= ratio;
            }

            renderCrop();
        });

        resetBtn.addEventListener("click", resetCrop);

        stage.addEventListener("pointerdown", function (event) {
            if (!image.src) return;

            dragging = true;
            lastX = event.clientX;
            lastY = event.clientY;
            stage.classList.add("is-dragging");

            try {
                stage.setPointerCapture(event.pointerId);
            } catch (e) {}
        });

        stage.addEventListener("pointermove", function (event) {
            if (!dragging) return;

            offsetX += event.clientX - lastX;
            offsetY += event.clientY - lastY;
            lastX = event.clientX;
            lastY = event.clientY;
            renderCrop();
        });

        function endDrag(event) {
            dragging = false;
            stage.classList.remove("is-dragging");

            try {
                stage.releasePointerCapture(event.pointerId);
            } catch (e) {}
        }

        stage.addEventListener("pointerup", endDrag);
        stage.addEventListener("pointercancel", endDrag);

        closeButtons.forEach(function (button) {
            button.addEventListener("click", function () {
                closeModal(true);
            });
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && modal.classList.contains("open")) {
                closeModal(true);
            }
        });

        window.addEventListener("resize", function () {
            if (modal.classList.contains("open") && image.naturalWidth) {
                resetCrop();
            }
        });

        saveBtn.addEventListener("click", function () {
            if (!image.naturalWidth || !image.naturalHeight) {
                setStatus("The image is still loading. Try again in a moment.", "error");
                return;
            }

            saveBtn.disabled = true;
            saveBtn.textContent = "Saving...";
            setStatus("Uploading cropped photo...", "");

            const size = stageSize();
            clampOffsets();

            const displayedWidth = image.naturalWidth * scale;
            const displayedHeight = image.naturalHeight * scale;
            const left = size / 2 + offsetX - displayedWidth / 2;
            const top = size / 2 + offsetY - displayedHeight / 2;

            let sourceX = -left / scale;
            let sourceY = -top / scale;
            const sourceSize = size / scale;

            sourceX = Math.max(
                0,
                Math.min(image.naturalWidth - sourceSize, sourceX)
            );
            sourceY = Math.max(
                0,
                Math.min(image.naturalHeight - sourceSize, sourceY)
            );

            const canvas = document.createElement("canvas");
            canvas.width = 800;
            canvas.height = 800;

            const ctx = canvas.getContext("2d", { alpha: false });
            if (!ctx) {
                saveBtn.disabled = false;
                saveBtn.textContent = "Save Photo";
                setStatus("Your browser could not prepare the cropped image.", "error");
                return;
            }

            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(
                image,
                sourceX,
                sourceY,
                sourceSize,
                sourceSize,
                0,
                0,
                canvas.width,
                canvas.height
            );

            canvas.toBlob(
                async function (blob) {
                    if (!blob) {
                        saveBtn.disabled = false;
                        saveBtn.textContent = "Save Photo";
                        setStatus("Could not crop this image. Please try another photo.", "error");
                        return;
                    }

                    const formData = new FormData();
                    formData.append(
                        "profile_photo",
                        blob,
                        "profile-photo-" + Date.now() + ".jpg"
                    );

                    const token =
                        (window.getCsrfToken && window.getCsrfToken()) ||
                        (document.querySelector('meta[name="csrf-token"]') || {}).content ||
                        "";

                    try {
                        const response = await fetch(uploadUrl, {
                            method: "POST",
                            body: formData,
                            headers: {
                                "X-CSRF-Token": token,
                                "X-Requested-With": "XMLHttpRequest"
                            },
                            credentials: "same-origin"
                        });

                        let data = {};
                        try {
                            data = await response.json();
                        } catch (e) {}

                        if (!response.ok || !data.success) {
                            throw new Error(data.error || "The photo could not be saved.");
                        }

                        if (preview && data.photo_url) {
                            preview.src =
                                data.photo_url +
                                (data.photo_url.includes("?") ? "&" : "?") +
                                "v=" +
                                Date.now();
                        }

                        closeModal(true);
                        setStatus("Profile photo saved successfully.", "success");
                    } catch (error) {
                        setStatus(
                            error && error.message
                                ? error.message
                                : "The photo could not be saved.",
                            "error"
                        );
                    } finally {
                        saveBtn.disabled = false;
                        saveBtn.textContent = "Save Photo";
                    }
                },
                "image/jpeg",
                0.93
            );
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initProfileCropper);
    } else {
        initProfileCropper();
    }
})();