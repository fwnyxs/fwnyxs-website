const menu=document.querySelector('.menu'), mobile=document.querySelector('.mobile');
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')==='true';menu.setAttribute('aria-expanded',String(!open));mobile.classList.toggle('open',!open);document.body.style.overflow=open?'':'hidden'});
mobile?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{menu.setAttribute('aria-expanded','false');mobile.classList.remove('open');document.body.style.overflow=''}));
const obs=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)e.target.classList.add('seen')}),{threshold:.1});document.querySelectorAll('.section,.feature,.release,.row').forEach(e=>obs.observe(e));
