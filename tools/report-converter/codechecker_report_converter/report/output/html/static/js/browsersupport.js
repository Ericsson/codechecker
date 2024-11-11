function setNonCompatibleBrowserMessage() {
  document.body.innerHTML =
    '<h2 style="margin-left: 20px;">Your browser is not compatible with CodeChecker Viewer!</h2> \
     <p style="margin-left: 20px;">The version required for the following browsers are:</p> \
     <ul style="margin-left: 20px;"> \
     <li>Internet Explorer: version 9 or newer</li> \
     <li>Firefox: version 22.0 or newer</li> \
     </ul>';
}

// http://stackoverflow.com/questions/5916900/how-can-you-detect-the-version-of-a-browser
var browserVersion = (function(){
  var ua = navigator.userAgent, tem,
    M = ua.match(/(opera|chrome|safari|firefox|msie|trident(?=\/))\/?\s*(\d+)/i) || [];

  if (/trident/i.test(M[1])) {
    tem = /\brv[ :]+(\d+)/g.exec(ua) || [];
    return 'IE ' + (tem[1] || '');
  }

  if (M[1] === 'Chrome') {
    tem = ua.match(/\b(OPR|Edge)\/(\d+)/);
    if (tem != null) return tem.slice(1).join(' ').replace('OPR', 'Opera');
  }

  M = M[2] ? [M[1], M[2]] : [navigator.appName, navigator.appVersion, '-?'];
  if ((tem = ua.match(/version\/(\d+)/i)) != null) M.splice(1, 1, tem[1]);
    return M.join(' ');
})();

var pos = browserVersion.indexOf(' ');
var browser = browserVersion.substr(0, pos);
var version = parseInt(browserVersion.substr(pos + 1));

var browserCompatible
  = browser === 'Firefox'
  ? version >= 22
  : browser === 'IE'
  ? version >= 9
  : true;
