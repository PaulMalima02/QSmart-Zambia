document.addEventListener('DOMContentLoaded', () => {
  // Password visibility toggle
  document.querySelectorAll('[data-toggle-password]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-toggle-password');
      const input = document.getElementById(id);
      if (!input) return;
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.innerHTML = show ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
    });
  });

  // OTP digit boxes
  const boxes = document.querySelectorAll('.otp-digit');
  if (boxes.length) {
    const hidden = document.getElementById('otpHidden');
    const form = document.getElementById('otpForm');

    function syncHidden() {
      const code = Array.from(boxes).map(b => b.value).join('');
      if (hidden) hidden.value = code;
      return code;
    }

    boxes.forEach((box, idx) => {
      box.addEventListener('input', (e) => {
        const v = e.target.value.replace(/\D/g, '').slice(-1);
        e.target.value = v;
        if (v && idx < boxes.length - 1) {
          boxes[idx + 1].focus();
        }
        const code = syncHidden();
        if (code.length === 6 && form) {
          form.submit();
        }
      });

      box.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !box.value && idx > 0) {
          boxes[idx - 1].focus();
        }
      });

      box.addEventListener('paste', (e) => {
        e.preventDefault();
        const paste = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '').slice(0, 6);
        paste.split('').forEach((ch, i) => {
          if (boxes[i]) boxes[i].value = ch;
        });
        const code = syncHidden();
        if (code.length === 6 && form) form.submit();
        else if (boxes[Math.min(paste.length, boxes.length - 1)]) {
          boxes[Math.min(paste.length, boxes.length - 1)].focus();
        }
      });
    });

    // Focus first box
    boxes[0].focus();
  }

  // Resend countdown timer
  const cfg = window.QSMART_OTP || {};
  let remaining = parseInt(cfg.resendRemaining || 0, 10);
  if (remaining > 0) {
    const btns = document.querySelectorAll('.resend-btn');
    const timers = document.querySelectorAll('.resend-timer');
    const countdowns = document.querySelectorAll('.countdown');

    btns.forEach(b => { b.disabled = true; });
    timers.forEach(t => t.classList.remove('d-none'));

    const interval = setInterval(() => {
      remaining -= 1;
      countdowns.forEach(c => { c.textContent = remaining; });
      if (remaining <= 0) {
        clearInterval(interval);
        btns.forEach(b => { b.disabled = false; });
        timers.forEach(t => t.classList.add('d-none'));
      }
    }, 1000);
  }
});
