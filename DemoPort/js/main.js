(() => {
  const root = document.documentElement;
  root.classList.add('js');

  // ---- 테마 (시스템 설정 따름 + 수동 전환) ----
  const themeBtn = document.getElementById('themeBtn');
  const themeIcon = document.getElementById('themeIcon');
  const mq = window.matchMedia('(prefers-color-scheme: dark)');

  const isDark = () => {
    const t = root.getAttribute('data-theme');
    return t ? t === 'dark' : mq.matches;
  };
  const syncIcon = () => {
    themeIcon.textContent = isDark() ? '☀️' : '🌙';
    themeBtn.setAttribute('aria-pressed', String(isDark()));
  };
  themeBtn.addEventListener('click', () => {
    const next = isDark() ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
    syncIcon();
  });
  mq.addEventListener('change', syncIcon);
  syncIcon();

  // ---- 스크롤 등장 애니메이션 ----
  const items = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('show');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    items.forEach((el, i) => {
      el.style.transitionDelay = `${(i % 3) * 80}ms`;
      io.observe(el);
    });
  } else {
    items.forEach(el => el.classList.add('show'));
  }

  // ---- 이메일 복사 ----
  const copyBtn = document.getElementById('copyBtn');
  const toast = document.getElementById('toast');
  const mail = document.getElementById('mail').textContent.trim();
  let timer;

  const say = msg => {
    toast.textContent = msg;
    clearTimeout(timer);
    timer = setTimeout(() => { toast.textContent = ''; }, 2000);
  };

  const fallbackCopy = () => {
    const ta = document.createElement('textarea');
    ta.value = mail;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch (e) {}
    ta.remove();
    return ok;
  };

  copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(mail);
      say('이메일 주소를 복사했습니다');
    } catch (e) {
      say(fallbackCopy() ? '이메일 주소를 복사했습니다' : '복사에 실패했습니다. 직접 선택해 복사해 주세요');
    }
  });
})();
