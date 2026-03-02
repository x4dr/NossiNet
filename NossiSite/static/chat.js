document.addEventListener("DOMContentLoaded", async () => {
    const btn = document.getElementById("join-video-btn");
    const input = document.getElementById("room-code-input");
    const wrapper = document.getElementById("livekit-wrapper");
    const container = document.getElementById("livekit-container");
    const micBtn = document.getElementById("toggle-mic-btn");
    const camBtn = document.getElementById("toggle-cam-btn");
    const leaveBtn = document.getElementById("leave-video-btn");
    const msgInput = document.getElementById("message_data");

    let room = null;

    if (btn) btn.addEventListener("click", async () => {
        let roomCode = document.getElementById("room-code-input").value.trim().toLowerCase();
        if (!roomCode) {
            roomCode = Math.random().toString(36).substring(2, 10);
            document.getElementById("room-code-input").value = roomCode;
        }

        btn.disabled = true;
        btn.innerText = "Connecting...";
        try {
            const response = await fetch(`/chat/livekit-token/${roomCode}`);
            if (!response.ok) throw new Error("Failed to get token");
            const data = await response.json();

            wrapper.style.display = "block";
            btn.style.display = "none";
            const lkStart = document.getElementById("livekit-start");
            if (lkStart) lkStart.style.display = "none";

            room = new window.LivekitClient.Room({
                adaptiveStream: true,
                dynacast: true,
            });

            const updateParticipantList = () => {
                const list = document.getElementById("participant-list");
                const count = document.getElementById("participant-count");

                let participants = [room.localParticipant, ...Array.from(room.remoteParticipants.values())];
                if (count) count.innerText = participants.length;

                if (list) {
                    list.innerHTML = "";
                    participants.forEach(p => {
                        const badge = document.createElement("div");
                        badge.id = `badge-${p.identity}`;
                        badge.className = "participant-name-badge";
                        badge.innerText = p.name || p.identity || "Unknown";
                        if (p.isSpeaking) badge.classList.add("speaking");
                        list.appendChild(badge);
                    });
                }
            };

            room.on(window.LivekitClient.RoomEvent.ParticipantConnected, updateParticipantList);

            room.on(window.LivekitClient.RoomEvent.ActiveSpeakersChanged, (speakers) => {
                document.querySelectorAll(".speaking").forEach(el => el.classList.remove("speaking"));
                speakers.forEach(p => {
                    const tile = document.getElementById(`participant-${p.identity}`);
                    if (tile) {
                        tile.classList.add("speaking");
                        const label = tile.querySelector('.participant-label');
                        if (label) label.classList.add("speaking");
                    }
                    const badge = document.getElementById(`badge-${p.identity}`);
                    if (badge) badge.classList.add("speaking");
                });
            });

            room.on(window.LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
                attachTrack(track, participant);
            });

            room.on(window.LivekitClient.RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
                track.detach();
                updateParticipantTile(participant);
            });

            room.on(window.LivekitClient.RoomEvent.ParticipantDisconnected, (participant) => {
                const tile = document.getElementById(`participant-${participant.identity}`);
                if (tile) tile.remove();
                const badge = document.getElementById(`badge-${participant.identity}`);
                if (badge) badge.remove();
                const count = document.getElementById("participant-count");
                if (count) count.innerText = room.remoteParticipants.size + 1;
            });

            room.on(window.LivekitClient.RoomEvent.LocalTrackPublished, (publication, participant) => {
                if (publication.track) attachTrack(publication.track, participant);
            });

            room.on(window.LivekitClient.RoomEvent.LocalTrackUnpublished, (publication, participant) => {
                if (publication.track) publication.track.detach();
                updateParticipantTile(participant);
            });

            await room.connect(data.url, data.token);

            const roomNameEl = document.getElementById("current-room-name");
            if (roomNameEl) roomNameEl.innerText = roomCode;
            updateParticipantList();

            // Attach tracks from participants already in the room
            room.remoteParticipants.forEach((participant) => {
                participant.videoTrackPublications.forEach((publication) => {
                    if (publication.isSubscribed && publication.track) {
                        attachTrack(publication.track, participant);
                    }
                });
                participant.audioTrackPublications.forEach((publication) => {
                    if (publication.isSubscribed && publication.track) {
                        attachTrack(publication.track, participant);
                    }
                });
            });

            // Enable camera and mic
            await room.localParticipant.setCameraEnabled(false);
            await room.localParticipant.setMicrophoneEnabled(true);

            micBtn.onclick = async () => {
                const isEnabled = room.localParticipant.isMicrophoneEnabled;
                await room.localParticipant.setMicrophoneEnabled(!isEnabled);
                if (isEnabled) {
                    micBtn.classList.add("active-toggle");
                    micBtn.innerText = "Unmute Mic";
                } else {
                    micBtn.classList.remove("active-toggle");
                    micBtn.innerText = "Mute Mic";
                }
            };

            camBtn.onclick = async () => {
                const isEnabled = room.localParticipant.isCameraEnabled;
                await room.localParticipant.setCameraEnabled(!isEnabled);
                camBtn.innerText = !isEnabled ? "Stop Camera" : "Start Camera";
                if (!isEnabled) {
                    camBtn.classList.add("active-toggle");
                    camBtn.innerText = "Stop Camera";
                } else {
                    camBtn.classList.remove("active-toggle");
                    camBtn.innerText = "Start Camera";
                }
            };

            leaveBtn.onclick = () => {
                room.disconnect();
                wrapper.style.display = "none";
                btn.style.display = "block";
                const lkStart = document.getElementById("livekit-start");
                if (lkStart) lkStart.style.display = "flex";
                btn.disabled = false;
                btn.innerText = "Join Video Call";
                container.innerHTML = "";
                const pList = document.getElementById("participant-list");
                if (pList) pList.innerHTML = "";
                const pCount = document.getElementById("participant-count");
                if (pCount) pCount.innerText = "0";
                micBtn.classList.remove("active-toggle");
                camBtn.classList.remove("active-toggle");
                micBtn.innerText = "Mute Mic";
                camBtn.innerText = "Start Camera";
            };

        } catch (e) {
            console.error("Failed to connect to LiveKit", e);
            btn.disabled = false;
            btn.innerText = "Join Video Call (Failed)";
        }
    });

    function attachTrack(track, participant) {
        let tile = document.getElementById(`participant-${participant.identity}`);
        if (!tile) {
            tile = document.createElement("div");
            tile.className = "participant-tile";
            tile.id = `participant-${participant.identity}`;

            const label = document.createElement("div");
            label.className = "participant-label";
            label.innerText = participant.name || participant.identity || "Unknown";
            tile.appendChild(label);

            if (participant === room.localParticipant) {
                tile.classList.add("local-pip");
                wrapper.appendChild(tile);
                makeDraggable(tile, wrapper);
            } else {
                tile.onclick = (e) => {
                    if (e.target.tagName.toLowerCase() === 'input') return; // ignore slider clicks
                    if (tile.classList.contains("focused")) {
                        tile.classList.remove("focused");
                        container.classList.remove("focus-mode");
                    } else {
                        document.querySelectorAll(".participant-tile.focused").forEach(el => el.classList.remove("focused"));
                        tile.classList.add("focused");
                        container.classList.add("focus-mode");
                    }
                };
                container.appendChild(tile);
            }
        }

        if (track.kind === window.LivekitClient.Track.Kind.Video) {
            const element = track.attach();
            const existingVideo = tile.querySelector("video");
            if (existingVideo) existingVideo.remove();
            tile.prepend(element);
        } else if (track.kind === window.LivekitClient.Track.Kind.Audio) {
            if (participant !== room.localParticipant) {
                const element = track.attach();
                tile.appendChild(element);
                const volContainer = document.createElement("div");
                volContainer.className = "volume-control";
                const volInput = document.createElement("input");
                volInput.type = "range";
                volInput.min = "0";
                volInput.max = "1";
                volInput.step = "0.05";
                volInput.value = "1";
                volInput.title = "Volume";
                volInput.oninput = (e) => {
                    element.volume = e.target.value;
                };
                volContainer.appendChild(volInput);
                tile.appendChild(volContainer);
            }
        }
    }

    function updateParticipantTile(participant) {
        const tile = document.getElementById(`participant-${participant.identity}`);
        if (tile) {
            let hasVideo = false;
            participant.videoTrackPublications.forEach((pub) => {
                if (pub.track) hasVideo = true;
            });
            if (!hasVideo) {
                const video = tile.querySelector("video");
                if (video) video.remove();
            }
        }
    }

    function makeDraggable(el, wrapperEl) {
        let isDragging = false;
        let startX, startY, initialX, initialY;

        el.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            initialX = el.offsetLeft;
            initialY = el.offsetTop;
            el.style.transition = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            el.style.left = `${initialX + dx}px`;
            el.style.top = `${initialY + dy}px`;
            el.style.right = 'auto';
            el.style.bottom = 'auto';
        });

        document.addEventListener('mouseup', () => {
            if (!isDragging) return;
            isDragging = false;
            el.style.transition = 'all 0.3s ease';

            const rect = el.getBoundingClientRect();
            const wrapperRect = wrapperEl.getBoundingClientRect();

            const toLeft = rect.left - wrapperRect.left;
            const toRight = wrapperRect.right - rect.right;
            const toTop = rect.top - wrapperRect.top;
            const toBottom = wrapperRect.bottom - rect.bottom;

            if (toRight < toLeft) {
                el.style.right = '10px';
                el.style.left = 'auto';
            } else {
                el.style.left = '10px';
                el.style.right = 'auto';
            }

            if (toBottom < toTop) {
                el.style.bottom = '10px';
                el.style.top = 'auto';
            } else {
                el.style.top = '10px';
                el.style.bottom = 'auto';
            }

            setTimeout(() => {
                el.style.transition = '';
            }, 300);
        });
    }

    // Command History Logic
    let prevCommand = [];
    let commandCount = 0;
    let keyCount = 0;

    document.addEventListener("keydown", (event) => {
        if (!msgInput) return;

        // Space to focus if not already focusing an input/textarea
        const tag = document.activeElement.tagName.toLowerCase();
        if (event.key === " " && tag !== "input" && tag !== "textarea") {
            msgInput.focus();
            event.preventDefault();
        }

        // ArrowUp/Down for history
        if (document.activeElement === msgInput) {
            if (event.key === "ArrowUp") {
                keyCount++;
                if (keyCount > commandCount) keyCount = commandCount;
                if (commandCount > 0 && prevCommand[commandCount - keyCount] !== undefined) {
                    msgInput.value = prevCommand[commandCount - keyCount];
                }
                event.preventDefault();
            } else if (event.key === "ArrowDown") {
                keyCount--;
                if (keyCount < 0) keyCount = 0;
                if (keyCount > 0 && prevCommand[commandCount - keyCount] !== undefined) {
                    msgInput.value = prevCommand[commandCount - keyCount];
                } else {
                    msgInput.value = "";
                }
                event.preventDefault();
            }
        }
    });

    // Capture history on send
    document.addEventListener("htmx:wsBeforeSend", function (event) {
        if (msgInput && msgInput.value.trim() !== "") {
            prevCommand.push(msgInput.value);
            commandCount = prevCommand.length;
            keyCount = 0;
        }
    });

    updateRelativeTimes();
});

function updateRelativeTimes() {
    document.querySelectorAll(".timestamp").forEach(function (element) {
        const dateString = element.getAttribute("datetime");
        if (!dateString) return;
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return; // Safety check for invalid dates

        const tooltipId = element.getAttribute("aria-describedby");
        const tooltip = document.getElementById(tooltipId);

        if (tooltip) {
            const y = date.getFullYear();
            const m = String(date.getMonth() + 1).padStart(2, '0');
            const d = String(date.getDate()).padStart(2, '0');
            const hh = String(date.getHours()).padStart(2, '0');
            const mm = String(date.getMinutes()).padStart(2, '0');
            const weekday = date.toLocaleDateString(undefined, { weekday: 'long' });

            tooltip.innerText = `${weekday}, ${y}/${m}/${d} ${hh}:${mm}`;
        }

        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        let relative = "";
        if (diff < 5) relative = "just now";
        else if (diff < 60) relative = diff + " seconds ago";
        else if (diff < 120) relative = "1 minute ago";
        else if (diff < 3600) relative = Math.floor(diff / 60) + " minutes ago";
        else if (diff < 7200) relative = "1 hour ago";
        else if (diff < 86400) relative = Math.floor(diff / 3600) + " hours ago";
        else if (diff < 172800) relative = "1 day ago";
        else relative = Math.floor(diff / 86400) + " days ago";

        element.innerText = relative;
    });
}

document.addEventListener("htmx:wsAfterMessage", function (event) {
    const chatbox = document.getElementById("chatbox");
    if (chatbox) chatbox.scrollTop = chatbox.scrollHeight;
    updateRelativeTimes();
});

setInterval(updateRelativeTimes, 30000);

document.addEventListener("htmx:wsAfterSend", function (event) {
    const msgInput = document.getElementById("message_data");
    if (msgInput) msgInput.value = "";
});
