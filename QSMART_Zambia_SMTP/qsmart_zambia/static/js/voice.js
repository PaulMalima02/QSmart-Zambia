/**
 * WhatsApp-style hold/click mic recorder for QSMART query forms.
 * Requires: #micBtn, #voiceFile (hidden input type=file), #recStatus, form enctype multipart
 */
(function () {
  function initRecorder(root) {
    root = root || document;
    const micBtn = root.querySelector('#micBtn') || root.querySelector('.mic-btn');
    const voiceFile = root.querySelector('#voiceFile') || root.querySelector('input[name="voice_note"]');
    const statusEl = root.querySelector('#recStatus') || root.querySelector('.rec-status');
    if (!micBtn || !voiceFile) return;

    let mediaRecorder = null;
    let chunks = [];
    let recording = false;
    let stream = null;

    function setStatus(msg, recordingOn) {
      if (statusEl) statusEl.textContent = msg || '';
      micBtn.classList.toggle('recording', !!recordingOn);
      micBtn.setAttribute('aria-pressed', recordingOn ? 'true' : 'false');
      const icon = micBtn.querySelector('i');
      if (icon) {
        icon.className = recordingOn ? 'bi bi-stop-fill' : 'bi bi-mic-fill';
      }
    }

    async function start() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatus('Microphone not supported in this browser. Use attach to upload audio.');
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        chunks = [];
        const mime = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' :
          (MediaRecorder.isTypeSupported('audio/ogg') ? 'audio/ogg' : '');
        mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
        mediaRecorder.onstop = () => {
          const type = mediaRecorder.mimeType || 'audio/webm';
          const ext = type.includes('ogg') ? 'ogg' : 'webm';
          const blob = new Blob(chunks, { type: type });
          const file = new File([blob], 'voice_note.' + ext, { type: type });
          const dt = new DataTransfer();
          dt.items.add(file);
          voiceFile.files = dt.files;
          setStatus('Voice note ready (' + Math.round(blob.size / 1024) + ' KB). Send when ready.');
          if (stream) stream.getTracks().forEach(t => t.stop());
        };
        mediaRecorder.start();
        recording = true;
        setStatus('Recording… tap mic to stop', true);
      } catch (err) {
        setStatus('Microphone permission denied or unavailable.');
        console.warn(err);
      }
    }

    function stop() {
      if (mediaRecorder && recording) {
        mediaRecorder.stop();
        recording = false;
      }
    }

    micBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (recording) stop();
      else start();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-voice-composer]').forEach(initRecorder);
    if (document.getElementById('micBtn')) initRecorder(document);
  });
})();
