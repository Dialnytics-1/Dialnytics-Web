'use strict';
(() => {
  const header = document.querySelector('.site-header');
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.getElementById('primary-navigation');
  const menus = Array.from(document.querySelectorAll('.nav-menu'));
  function closeMenus(except) { menus.forEach(menu => { if (menu !== except) menu.open = false; }); }
  toggle?.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    nav.classList.toggle('open', open);
    if (!open) closeMenus();
  });
  menus.forEach(menu => menu.addEventListener('toggle', () => { if (menu.open) closeMenus(menu); }));
  document.addEventListener('click', event => { if (!header?.contains(event.target)) closeMenus(); });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const openMenu = menus.find(menu => menu.open);
    if (openMenu) { openMenu.open = false; openMenu.querySelector('summary')?.focus(); }
    else if (nav?.classList.contains('open')) { toggle.click(); toggle.focus(); }
  });
  window.matchMedia('(min-width: 1001px)').addEventListener('change', event => {
    if (event.matches && toggle) { nav.classList.remove('open'); toggle.setAttribute('aria-expanded','false'); }
  });
  const search = document.getElementById('collection-search');
  search?.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase(); let visible = 0;
    document.querySelectorAll('.collection-card').forEach(card => {
      card.hidden = !card.textContent.toLowerCase().includes(query);
      if (!card.hidden) visible += 1;
    });
    document.getElementById('collection-empty').hidden = visible > 0;
  });
  const tabs = Array.from(document.querySelectorAll('[data-tour-tab]'));
  const activate = index => {
    tabs.forEach((tab, i) => { tab.setAttribute('aria-selected',String(i === index)); tab.tabIndex = i === index ? 0 : -1; document.getElementById('tour-panel-' + i).hidden = i !== index; });
  };
  tabs.forEach((tab,index) => {
    tab.addEventListener('click', () => activate(index));
    tab.addEventListener('keydown', event => {
      let target;
      if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') target = (index + tabs.length - 1) % tabs.length;
      else if (event.key === 'Home') target = 0;
      else if (event.key === 'End') target = tabs.length - 1;
      if (target !== undefined) { event.preventDefault(); activate(target); tabs[target].focus(); }
    });
  });
})();
