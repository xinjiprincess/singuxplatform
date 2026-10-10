(() => {
  const embedded = window.self !== window.top;
  document.documentElement.classList.toggle('reader-embedded', embedded);
  const install = () => {
    const toolbar = document.querySelector('.docs-toolbar');
    if (!toolbar || toolbar.querySelector('.reader-actions')) return;
    const actions = document.createElement('div');
    actions.className = 'reader-actions';
    const add = (title, icon, action) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.title = title;
      button.setAttribute('aria-label', title);
      const glyph = document.createElement('i');
      glyph.className = icon;
      glyph.setAttribute('aria-hidden', 'true');
      button.append(glyph);
      button.addEventListener('click', action);
      actions.append(button);
    };
    add('独立窗口阅读', 'el-icon-top-right', () => window.open(location.href, '_blank', 'noopener,noreferrer'));
    if (document.fullscreenEnabled) {
      add('切换全屏', 'el-icon-full-screen', async () => {
        try {
          if (document.fullscreenElement) await document.exitFullscreen();
          else await document.documentElement.requestFullscreen();
        } catch { window.open(location.href, '_blank', 'noopener,noreferrer'); }
      });
    }
    toolbar.append(actions);
  };
  new MutationObserver(install).observe(document.body, { childList: true, subtree: true });
  install();
})();
