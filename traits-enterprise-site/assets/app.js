const menu = document.querySelector('.menu');
const mobileNav = document.querySelector('.mobile-nav');
const hero = document.querySelector('.hero');
const promiseStrip = document.querySelector('.promise-strip');
const googleReviewsUrl = 'https://maps.app.goo.gl/1JncS6G183YpHBFH6';

document.querySelectorAll('a[href="https://share.google/thNQYvOfQDnnlgZl7"]').forEach((link) => {
  link.href = googleReviewsUrl;
});

if (hero && promiseStrip) hero.after(promiseStrip);

document.querySelectorAll('main > section, footer').forEach((section) => section.classList.add('reveal'));
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) entry.target.classList.add('is-visible');
  });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach((section) => revealObserver.observe(section));

menu?.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') === 'true';
  menu.setAttribute('aria-expanded', String(!open));
  mobileNav.classList.toggle('open', !open);
  document.body.style.overflow = open ? '' : 'hidden';
});
mobileNav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  menu.setAttribute('aria-expanded', 'false');
  mobileNav.classList.remove('open');
  document.body.style.overflow = '';
}));
