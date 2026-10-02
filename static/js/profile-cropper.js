(function () {
    "use strict";

    function initProfileCropper() {
        const input = document.getElementById("profile_photo");
        const chooseBtn = document.getElementById("chooseProfilePhotoBtn");
        const modal = document.getElementById("profileCropModal");
        const stage = document.getElementById("profileCropStage");
        const image = document.getElementById("profileCropImage");
        const cropBox = document.getElementById("profileCropBox");
        const resetBtn = document.getElementById("profileCropReset");
        const saveBtn = document.getElementById("profileCropSave");
        const status = document.getElementById("profilePhotoStatus");
        const preview = document.getElementById("profilePhotoPreview");

        if (!input || !chooseBtn || !modal || !stage || !image || !cropBox || !resetBtn || !saveBtn) {
            return;
        }

        const closeButtons = modal.querySelectorAll("[data-crop-close]");
        const uploadUrl = input.dataset.uploadUrl || "/admin/profile-photo";

        let cropX = 0;
        let cropY = 0;
        let cropSize = 160;
        let imageBounds = null;
        let interaction = null;

        function setStatus(message, type) {
            if (!status) return;
            status.textContent = message || "";
            status.classList.remove("is-error", "is-success");
            if (type === "error") status.classList.add("is-error");
            if (type === "success") status.classList.add("is-success");
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
            interaction = null;
            if (clearFile) input.value = "";
            image.removeAttribute("src");
        }

        function readImage(file) {
            const reader = new FileReader();
            reader.onload = function () {
                image.onload = function () {
                    showModal();
                    requestAnimationFrame(resetCrop);
                };
                image.onerror = function () {
                    closeModal(true);
                    setStatus("This image could not be opened. Try a JPG, PNG, or WEBP file.", "error");
                };
                image.src = reader.result;
            };
            reader.onerror = function () {
                setStatus("This image could not be read.", "error");
            };
            reader.readAsDataURL(file);
        }

        function getImageBounds() {
            const stageRect = stage.getBoundingClientRect();
            const imageRect = image.getBoundingClientRect();

            return {
                left: imageRect.left - stageRect.left,
                top: imageRect.top - stageRect.top,
                width: imageRect.width,
                height: imageRect.height,
                right: imageRect.right - stageRect.left,
                bottom: imageRect.bottom - stageRect.top
            };
        }

        function renderCropBox() {
            cropBox.style.left = cropX + "px";
            cropBox.style.top = cropY + "px";
            cropBox.style.width = cropSize + "px";
            cropBox.style.height = cropSize + "px";
        }

        function resetCrop() {
            if (!image.naturalWidth || !image.naturalHeight) return;

            imageBounds = getImageBounds();
            cropSize = Math.max(
                90,
                Math.min(imageBounds.width, imageBounds.height) * 0.82
            );
            cropX = imageBounds.left + (imageBounds.width - cropSize) / 2;
            cropY = imageBounds.top + (imageBounds.height - cropSize) / 2;
            renderCropBox();
        }

        function clampMove(x, y) {
            if (!imageBounds) return { x: cropX, y: cropY };
            return {
                x: Math.min(
                    imageBounds.right - cropSize,
                    Math.max(imageBounds.left, x)
                ),
                y: Math.min(
                    imageBounds.bottom - cropSize,
                    Math.max(imageBounds.top, y)
                )
            };
        }

        function resizeFromHandle(handle, pointerX, pointerY) {
            if (!imageBounds || !interaction) return;

            const minSize = Math.min(
                90,
                imageBounds.width,
                imageBounds.height
            );

            let anchorX;
            let anchorY;
            let rawSize;
            let maxSize;
            let newX;
            let newY;

            if (handle === "nw") {
                anchorX = interaction.startX + interaction.startSize;
                anchorY = interaction.startY + interaction.startSize;
                rawSize = Math.max(anchorX - pointerX, anchorY - pointerY);
                maxSize = Math.min(
                    anchorX - imageBounds.left,
                    anchorY - imageBounds.top
                );
                cropSize = Math.min(maxSize, Math.max(minSize, rawSize));
                newX = anchorX - cropSize;
                newY = anchorY - cropSize;
            } else if (handle === "ne") {
                anchorX = interaction.startX;
                anchorY = interaction.startY + interaction.startSize;
                rawSize = Math.max(pointerX - anchorX, anchorY - pointerY);
                maxSize = Math.min(
                    imageBounds.right - anchorX,
                    anchorY - imageBounds.top
                );
                cropSize = Math.min(maxSize, Math.max(minSize, rawSize));
                newX = anchorX;
                newY = anchorY - cropSize;
            } else if (handle === "sw") {
                anchorX = interaction.startX + interaction.startSize;
                anchorY = interaction.startY;
                rawSize = Math.max(anchorX - pointerX, pointerY - anchorY);
                maxSize = Math.min(
                    anchorX - imageBounds.left,
                    imageBounds.bottom - anchorY
                );
                cropSize = Math.min(maxSize, Math.max(minSize, rawSize));
                newX = anchorX - cropSize;
                newY = anchorY;
            } else {
                anchorX = interaction.startX;
                anchorY = interaction.startY;
                rawSize = Math.max(pointerX - anchorX, pointerY - anchorY);
                maxSize = Math.min(
                    imageBounds.right - anchorX,
                    imageBounds.bottom - anchorY
                );
                cropSize = Math.min(maxSize, Math.max(minSize, rawSize));
                newX = anchorX;
                newY = anchorY;
            }

            cropX = newX;
            cropY = newY;
            renderCropBox();
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

            setStatus("", "");
            readImage(file);
        });

        cropBox.addEventListener("pointerdown", function (event) {
            if (!imageBounds) return;

            event.preventDefault();
            const stageRect = stage.getBoundingClientRect();
            const handleEl = event.target.closest("[data-handle]");
            const handle = handleEl ? handleEl.dataset.handle : null;

            interaction = {
                mode: handle ? "resize" : "move",
                handle: handle,
                pointerStartX: event.clientX - stageRect.left,
                pointerStartY: event.clientY - stageRect.top,
                startX: cropX,
                startY: cropY,
                startSize: cropSize
            };

            try {
                cropBox.setPointerCapture(event.pointerId);
            } catch (e) {}
        });

        cropBox.addEventListener("pointermove", function (event) {
            if (!interaction) return;

            const stageRect = stage.getBoundingClientRect();
            const pointerX = event.clientX - stageRect.left;
            const pointerY = event.clientY - stageRect.top;

            if (interaction.mode === "move") {
                const dx = pointerX - interaction.pointerStartX;
                const dy = pointerY - interaction.pointerStartY;
                const next = clampMove(
                    interaction.startX + dx,
                    interaction.startY + dy
                );
                cropX = next.x;
                cropY = next.y;
                renderCropBox();
            } else {
                resizeFromHandle(interaction.handle, pointerX, pointerY);
            }
        });

        function endInteraction(event) {
            interaction = null;
            try {
                cropBox.releasePointerCapture(event.pointerId);
            } catch (e) {}
        }

        cropBox.addEventListener("pointerup", endInteraction);
        cropBox.addEventListener("pointercancel", endInteraction);

        resetBtn.addEventListener("click", resetCrop);

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
                requestAnimationFrame(resetCrop);
            }
        });

        saveBtn.addEventListener("click", function () {
            if (!image.naturalWidth || !image.naturalHeight || !imageBounds) {
                setStatus("The image is still loading. Try again in a moment.", "error");
                return;
            }

            saveBtn.disabled = true;
            saveBtn.textContent = "Saving...";
            setStatus("Uploading cropped photo...", "");

            const stageRect = stage.getBoundingClientRect();
            const imageRect = image.getBoundingClientRect();
            const cropRect = cropBox.getBoundingClientRect();

            const sourceX =
                (cropRect.left - imageRect.left) *
                (image.naturalWidth / imageRect.width);
            const sourceY =
                (cropRect.top - imageRect.top) *
                (image.naturalHeight / imageRect.height);
            const sourceWidth =
                cropRect.width * (image.naturalWidth / imageRect.width);
            const sourceHeight =
                cropRect.height * (image.naturalHeight / imageRect.height);

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
            ctx.fillRect(0, 0, 800, 800);
            ctx.drawImage(
                image,
                sourceX,
                sourceY,
                sourceWidth,
                sourceHeight,
                0,
                0,
                800,
                800
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