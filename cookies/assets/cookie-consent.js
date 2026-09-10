(function(){
  var KEY = 'fwnyxs_cookie_consent';

  function getConsent(){
    try{ return JSON.parse(localStorage.getItem(KEY)); }
    catch(e){ return null; }
  }

  function setConsent(value){
    try{
      localStorage.setItem(KEY, JSON.stringify({ value: value, ts: Date.now() }));
    }catch(e){}
    document.dispatchEvent(new CustomEvent('fwnyxs:consent', { detail: value }));
  }

  function hideBanner(bar){
    bar.classList.remove('show');
    setTimeout(function(){ bar.remove(); }, 500);
  }

  function openBanner(){
    if(document.getElementById('cookieConsent')) return;

    var bar = document.createElement('div');
    bar.id = 'cookieConsent';
    bar.className = 'cookie-bar';
    bar.setAttribute('role', 'dialog');
    bar.setAttribute('aria-live', 'polite');
    bar.setAttribute('aria-label', 'Cookie preferences');

    bar.innerHTML =
      '<div class="cookie-bar-inner">' +
        '<div class="cookie-text">' +
          '<p class="mono cookie-label">FWNYXS / COOKIES</p>' +
          '<p>We use essential storage to run this site, and would like your permission for optional analytics storage to understand what\u2019s working. <a href="cookies.html">Read more</a>.</p>' +
        '</div>' +
        '<div class="cookie-actions">' +
          '<button type="button" class="cookie-btn ghost mono" id="cookieDecline">NECESSARY ONLY</button>' +
          '<button type="button" class="cookie-btn mono" id="cookieAccept">ACCEPT ALL</button>' +
        '</div>' +
      '</div>';

    document.body.appendChild(bar);

    requestAnimationFrame(function(){
      requestAnimationFrame(function(){ bar.classList.add('show'); });
    });

    document.getElementById('cookieAccept').addEventListener('click', function(){
      setConsent('all');
      hideBanner(bar);
    });
    document.getElementById('cookieDecline').addEventListener('click', function(){
      setConsent('necessary');
      hideBanner(bar);
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    if(!getConsent()) openBanner();

    document.querySelectorAll('.cookie-settings-link').forEach(function(el){
      el.addEventListener('click', function(e){
        e.preventDefault();
        openBanner();
      });
    });
  });

  window.fwnyxsCookiePrefs = {
    get: getConsent,
    open: openBanner,
    reset: function(){
      try{ localStorage.removeItem(KEY); }catch(e){}
      openBanner();
    }
  };
})();
